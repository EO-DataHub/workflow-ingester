import json
import logging
import os
import time
import traceback
from typing import Any

import boto3
import boto3.session
import botocore.client
import botocore.exceptions
import pulsar
import pulsar.exceptions
import yaml

from .ades_api import AdesApiClient

ILLEGAL_WORKFLOW_INPUTS_RAW = os.getenv("ILLEGAL_WORKFLOW_INPUTS", "token").split(",")
ILLEGAL_WORKFLOW_INPUTS = [input_name.strip().lower() for input_name in ILLEGAL_WORKFLOW_INPUTS_RAW]

ILLEGAL_WORKFLOW_STEPS_RAW = os.getenv("ILLEGAL_WORKFLOW_STEPS", "node_stage_in,node_stage_out").split(",")
ILLEGAL_WORKFLOW_STEPS = [step.strip().lower() for step in ILLEGAL_WORKFLOW_STEPS_RAW]

# create logger for stac fastapi ingester
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(filename="workflow-ingester.log", encoding="utf-8", level=logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# set the time converter to UTC
formatter.converter = time.gmtime

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


def copy_file(s3_client: botocore.client.BaseClient, bucket_name: str, source_key: str, dest_key: str) -> bool:
    """
    Move the chosen file to the correct location in the workspace.
    """
    try:
        logger.info("Copying workflow file from %s to %s", source_key, dest_key)
        copy_source = {"Bucket": bucket_name, "Key": source_key}
        s3_client.copy_object(CopySource=copy_source, Bucket=bucket_name, Key=dest_key)
        logger.info("Copied workflow file from %s to %s", source_key, dest_key)
        return True
    except Exception:
        logger.exception("Failed to copy workflow file from %s to %s", source_key, dest_key)
        return False


def delete_file(s3_client: botocore.client.BaseClient, bucket_name: str, key: str) -> bool:
    """
    Delete the chosen file from the workspace.
    """
    try:
        logger.info("Deleting workflow file from %s", key)
        s3_client.delete_object(Bucket=bucket_name, Key=key)
        logger.info("Deleted workflow file from %s", key)
        return True
    except Exception:
        logger.exception("Failed to delete workflow file from %s", key)
        return False


def get_s3_client() -> botocore.client.BaseClient:
    """
    Generate boto3 client ready for S3 data access
    """
    if os.getenv("AWS_ACCESS_KEY") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        session = boto3.session.Session(
            aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        )
        client = session.client("s3")

    else:
        client = boto3.client("s3")

    return client


def get_file_name(key: str) -> str:
    """
    Extract the file name from file key.
    """
    return key.rsplit("/", maxsplit=1)[-1]


def get_workspace(key: str) -> str:
    """
    Extract workspace from file key
    """
    return key.split("/")[-2]


def check_workflow_validity(data: dict[str, Any]) -> tuple[bool, str]:
    inputs = data.get("inputs", {})
    logger.debug("Checking workflow inputs: %s", inputs)
    steps = data.get("steps", {})
    logger.debug("Checking workflow steps: %s", steps)
    if isinstance(inputs, list):
        for input_item in inputs:
            if input_item["id"].lower() in ILLEGAL_WORKFLOW_INPUTS:
                return False, f"Input {input_item['id']} is not allowed in workflow"
    elif isinstance(inputs, dict):
        for key in inputs:
            if key.lower() in ILLEGAL_WORKFLOW_INPUTS:
                return False, f"Input {key} is not allowed in workflow"
    if isinstance(steps, list):
        for step in steps:
            for illegal_step in ILLEGAL_WORKFLOW_STEPS:
                if step["id"].lower().startswith(illegal_step):
                    return False, f"Step {step['id']} is not allowed in workflow"
    elif isinstance(steps, dict):
        for key in steps:
            for illegal_step in ILLEGAL_WORKFLOW_STEPS:
                if key.lower().startswith(illegal_step):
                    return False, f"Step {key} is not allowed in workflow"
    return True, data["id"]


def get_workflow_id(workflow: str) -> tuple[bool, str]:
    """
    Extract workflow id from workflow cwl file
    """
    try:
        workflow_dict = yaml.safe_load(workflow)
        for item in workflow_dict["$graph"]:
            if item.get("class") == "Workflow":
                success, details = check_workflow_validity(item)
                return success, details
    except yaml.YAMLError:
        logger.error("Could not parse workflow, invalid yaml")
    except KeyError:
        logger.error("Could not find workflow id in given workflow definition")
    return False, "Could not find Workflow class in CWL graph"


def get_file_from_s3(s3_client: botocore.client.BaseClient, bucket_name: str, key: str) -> str | None:
    """
    Get file from S3 bucket
    """
    try:
        data = s3_client.get_object(Bucket=bucket_name, Key=key)
        return data["Body"].read().decode("utf-8")
    except botocore.exceptions.ClientError:
        logger.exception("Failed to get object from S3")
        return None


def interpret_message(msg: str, ades_url: str, delay: int = 0) -> None:
    """
    Interpret Pulsar message to create, update or delete catalogs in S3.
    """
    # Configure ADES client to deploy workflow
    ades_api = AdesApiClient(ades_url)

    # Configure S3 client to interact with S3 bucket
    s3_client = get_s3_client()

    # Extract as JSON dictionary
    msg_json = json.loads(msg)

    # Extract keys
    added_keys = msg_json["added_keys"]
    updated_keys = msg_json["updated_keys"]
    deleted_keys = msg_json["deleted_keys"]

    if added_keys:
        added_keys.sort(key=lambda x: x.split(".")[-1])  # sort added keys by file type, cwl first

    if updated_keys:
        updated_keys.sort(key=lambda x: x.split(".")[-1])  # sort updated keys by file type, cwl first

    if deleted_keys:
        deleted_keys.sort(key=lambda x: x.split(".")[-1])  # sort deleted keys by file type, cwl first

    # Track added files as they are added
    added_workflows: list[str] = []

    # Track updated files as they are updated
    updated_workflows: list[str] = []

    # Track deleted files as they are deleted
    deleted_workflows: list[str] = []

    # Extract workspace name and bucket name
    bucket_name = msg_json["bucket_name"]

    for key in added_keys:
        workspace_name = get_workspace(key)
        if key.endswith(".cwl"):
            dest_key = f"deployed/{workspace_name}/{get_file_name(key)}"
            data_str = get_file_from_s3(s3_client, bucket_name, key)
            if data_str is None:
                logger.warning("Skipping workflow %s in workspace %s", key, workspace_name)
                continue
            success, details = get_workflow_id(data_str)
            if not success:
                logger.warning("Skipping workflow %s in workspace %s as %s", key, workspace_name, details)
                continue
            workflow_id = details
            if ades_api.create(workspace_name, workflow_id, data_str) and copy_file(
                s3_client, bucket_name, key, dest_key
            ):
                added_workflows.append(workflow_id)
                time.sleep(delay)
        if (
            key.endswith(".access-policy.json")
            and get_file_name(key).replace(".access-policy.json", "") in added_workflows
        ):
            dest_key = f"deployed/{workspace_name}/{get_file_name(key)}"
            copy_file(s3_client, bucket_name, key, dest_key)
    for key in updated_keys:
        workspace_name = get_workspace(key)
        if key.endswith(".cwl"):
            dest_key = f"deployed/{workspace_name}/{get_file_name(key)}"
            data_str = get_file_from_s3(s3_client, bucket_name, key)
            if data_str is None:
                logger.warning("Skipping key %s in workspace %s", key, workspace_name)
                continue
            success, details = get_workflow_id(data_str)
            if not success:
                logger.warning("Skipping key %s in workspace %s as %s", key, workspace_name, details)
                continue
            workflow_id = details
            if ades_api.update(workspace_name, workflow_id, data_str) and copy_file(
                s3_client, bucket_name, key, dest_key
            ):
                updated_workflows.append(workflow_id)
                time.sleep(delay)
        if (
            key.endswith(".access-policy.json")
            and get_file_name(key).replace(".access-policy.json", "") in updated_workflows
        ):
            dest_key = f"deployed/{workspace_name}/{get_file_name(key)}"
            copy_file(s3_client, bucket_name, key, dest_key)
    for key in deleted_keys:
        workspace_name = get_workspace(key)
        if key.endswith(".cwl"):
            dest_key = f"deployed/{workspace_name}/{get_file_name(key)}"
            data_str = get_file_from_s3(
                s3_client, bucket_name, dest_key
            )  # use dest_key as original key will have been deleted
            if data_str is None:
                logger.warning("Skipping key %s in workspace %s", key, workspace_name)
                continue
            # TODO: get workflow ID from filename, perhaps, as the file has been deleted
            success, details = get_workflow_id(data_str)
            if not success:
                logger.warning("Skipping key %s in workspace %s as %s", key, workspace_name, details)
                continue
            workflow_id = details
            if ades_api.delete(workspace_name, workflow_id) and delete_file(s3_client, bucket_name, dest_key):
                deleted_workflows.append(workflow_id)
        if (
            key.endswith(".access-policy.json")
            and get_file_name(key).replace(".access-policy.json", "") in deleted_workflows
        ):
            # only delete the policy if the workflow has been removed from the ADES
            dest_key = f"deployed/{workspace_name}/{get_file_name(key)}"
            delete_file(s3_client, bucket_name, dest_key)


def main(consumer: pulsar.Consumer, ades_url: str, delay: int = 0) -> None:
    """
    Accept messages from a Pulsar broker.
    """
    while True:
        msg = None
        try:
            logger.info("Waiting for message")
            msg = consumer.receive()
            logging.info("Parsing harvested message %s", msg.data())
            decoded_msg = msg.data().decode("utf-8")
            interpret_message(decoded_msg, ades_url, delay)
            consumer.acknowledge(msg)
        except Exception as err:
            logger.debug(traceback.format_exc())
            logger.error(err)
            if msg is not None:
                consumer.negative_acknowledge(msg)
            if str(err) == "Stop loop":
                break


if __name__ == "__main__":
    pulsar_url = os.environ.get("PULSAR_URL", "")
    topic = os.environ.get("PULSAR_TOPIC", "")
    identifier = os.environ.get("IDENTIFIER", "")
    ades_url = os.environ.get("ADES_URL", "")
    delay = int(os.environ.get("DELAY", 0))
    client = pulsar.Client(pulsar_url)
    if identifier:
        identifier = f"-{identifier}"
    consumer = client.subscribe(topic=topic, subscription_name=f"workspace-catalog-generator{identifier}")
    main(consumer, ades_url, delay)
