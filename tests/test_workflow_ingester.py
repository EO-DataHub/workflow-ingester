import json
from unittest import mock

import botocore

from workflow_ingester.__main__ import (
    copy_file,
    delete_file,
    get_file_from_s3,
    get_file_name,
    get_s3_client,
    get_workflow_id,
    get_workspace,
    interpret_message,
    main,
)


def test_copy_file():
    s3_client = mock.Mock()
    copy_file(s3_client, "test-bucket", "source-key", "dest-key")
    s3_client.copy_object.assert_called_once_with(
        CopySource={"Bucket": "test-bucket", "Key": "source-key"},
        Bucket="test-bucket",
        Key="dest-key",
    )


def test_delete_file():
    s3_client = mock.Mock()
    delete_file(s3_client, "test-bucket", "test-key")
    s3_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="test-key")


def test_get_s3_client(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    client = get_s3_client()
    assert isinstance(client, botocore.client.BaseClient)


def test_get_file_name():
    assert get_file_name("path/to/file.txt") == "file.txt"


def test_get_workspace():
    assert get_workspace("path/to/workspace/file.txt") == "workspace"


def test_get_workflow_id():
    workflow = """
    $graph:
      - id: test-workflow-id
    """
    assert get_workflow_id(workflow) == "test-workflow-id"


def test_get_workflow_id_invalid_yaml():
    workflow = "invalid: yaml: content"
    assert get_workflow_id(workflow) is None


def test_get_file_from_s3():
    s3_client = mock.Mock()
    s3_client.get_object.return_value = {
        "Body": mock.Mock(read=mock.Mock(return_value=b"test-content"))
    }
    assert get_file_from_s3(s3_client, "test-bucket", "test-key") == "test-content"


def test_interpret_message():
    msg = json.dumps(
        {
            "added_keys": ["path/to/workflow.cwl"],
            "updated_keys": [],
            "deleted_keys": [],
            "bucket_name": "test-bucket",
        }
    )
    ades_url = "http://test-ades-url"
    interpret_message(msg, ades_url)


@mock.patch("workflow_ingester.__main__.AdesApiClient")
@mock.patch("workflow_ingester.__main__.get_s3_client")
def test_interpret_message_create_workflow(mock_get_s3_client, mock_AdesApiClient):
    msg = json.dumps(
        {
            "added_keys": ["path/test-workspace/workflow.cwl"],
            "updated_keys": [],
            "deleted_keys": [],
            "bucket_name": "test-bucket",
        }
    )
    ades_url = "http://test-ades-url"

    mock_ades_api = mock.Mock()
    mock_s3_client = mock.Mock()
    mock_s3_client.get_object.return_value = {
        "Body": mock.Mock(read=mock.Mock(return_value=b"$graph:\n  - id: test-workflow-id"))
    }

    mock_AdesApiClient.return_value = mock_ades_api
    mock_get_s3_client.return_value = mock_s3_client

    interpret_message(msg, ades_url)

    mock_ades_api.create.assert_called_once_with(
        "test-workspace", "test-workflow-id", "$graph:\n  - id: test-workflow-id"
    )
    mock_s3_client.copy_object.assert_called_once_with(
        CopySource={"Bucket": "test-bucket", "Key": "path/test-workspace/workflow.cwl"},
        Bucket="test-bucket",
        Key="deployed/test-workspace/workflow.cwl",
    )


@mock.patch("workflow_ingester.__main__.AdesApiClient")
@mock.patch("workflow_ingester.__main__.get_s3_client")
def test_interpret_message_update_workflow(mock_get_s3_client, mock_AdesApiClient):
    msg = json.dumps(
        {
            "added_keys": [],
            "updated_keys": ["path/test-workspace/workflow.cwl"],
            "deleted_keys": [],
            "bucket_name": "test-bucket",
        }
    )
    ades_url = "http://test-ades-url"

    mock_ades_api = mock.Mock()
    mock_s3_client = mock.Mock()
    mock_s3_client.get_object.return_value = {
        "Body": mock.Mock(read=mock.Mock(return_value=b"$graph:\n  - id: test-workflow-id"))
    }

    mock_AdesApiClient.return_value = mock_ades_api
    mock_get_s3_client.return_value = mock_s3_client

    interpret_message(msg, ades_url)

    mock_ades_api.update.assert_called_once_with(
        "test-workspace", "test-workflow-id", "$graph:\n  - id: test-workflow-id"
    )
    mock_s3_client.copy_object.assert_called_once_with(
        CopySource={"Bucket": "test-bucket", "Key": "path/test-workspace/workflow.cwl"},
        Bucket="test-bucket",
        Key="deployed/test-workspace/workflow.cwl",
    )


@mock.patch("workflow_ingester.__main__.AdesApiClient")
@mock.patch("workflow_ingester.__main__.get_s3_client")
def test_interpret_message_delete_workflow(mock_get_s3_client, mock_AdesApiClient):
    msg = json.dumps(
        {
            "added_keys": [],
            "updated_keys": [],
            "deleted_keys": ["path/test-workspace/workflow.cwl"],
            "bucket_name": "test-bucket",
        }
    )
    ades_url = "http://test-ades-url"

    mock_ades_api = mock.Mock()
    mock_s3_client = mock.Mock()
    mock_s3_client.get_object.return_value = {
        "Body": mock.Mock(read=mock.Mock(return_value=b"$graph:\n  - id: test-workflow-id"))
    }

    mock_AdesApiClient.return_value = mock_ades_api
    mock_get_s3_client.return_value = mock_s3_client

    interpret_message(msg, ades_url)

    mock_ades_api.delete.assert_called_once_with("test-workspace", "test-workflow-id")
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket="test-bucket", Key="deployed/test-workspace/workflow.cwl"
    )


@mock.patch("workflow_ingester.__main__.AdesApiClient")
@mock.patch("workflow_ingester.__main__.get_s3_client")
def test_interpret_message_skip_invalid_workflow(mock_get_s3_client, mock_AdesApiClient):
    msg = json.dumps(
        {
            "added_keys": ["path/test-workspace/invalid_workflow.cwl"],
            "updated_keys": [],
            "deleted_keys": [],
            "bucket_name": "test-bucket",
        }
    )
    ades_url = "http://test-ades-url"

    mock_ades_api = mock.Mock()
    mock_s3_client = mock.Mock()
    mock_s3_client.get_object.return_value = {
        "Body": mock.Mock(read=mock.Mock(return_value=b"invalid: yaml: content"))
    }

    mock_AdesApiClient.return_value = mock_ades_api
    mock_get_s3_client.return_value = mock_s3_client

    interpret_message(msg, ades_url)

    mock_ades_api.create.assert_not_called()
    mock_s3_client.copy_object.assert_not_called()


@mock.patch("workflow_ingester.__main__.get_workflow_id")
@mock.patch("workflow_ingester.__main__.get_s3_client")
@mock.patch("workflow_ingester.__main__.AdesApiClient")
def test_policy_files(MockAdesApiClient, MockGetS3Client, MockGetWorkflowId):
    # Create mock instances
    mock_ades_api = MockAdesApiClient.return_value
    mock_s3_client = MockGetS3Client.return_value

    # Define mock message
    mock_message = json.dumps(
        {
            "added_keys": ["workspace1/workflow1.access-policy.json", "workspace1/workflow1.cwl"],
            "updated_keys": [
                "workspace2/workflow2.access-policy.json",
                "workspace2/workflow2.cwl",
                "workspace2/workflow2-1.access-policy.json",
            ],
            "deleted_keys": ["workspace3/workflow3.access-policy.json"],
            "bucket_name": "test-bucket",
        }
    )

    ades_url = "http://test-ades-url"

    # Mock S3 client methods
    mock_s3_client.get_object.return_value = {
        "Body": mock.Mock(read=lambda: b"$graph:\n  - id: test-workflow-id")
    }
    mock_s3_client.copy_object.return_value = None
    mock_s3_client.delete_object.return_value = None

    # Mock get workflow id method
    MockGetWorkflowId.side_effect = ["workflow1", "workflow2", "workflow3"]

    # Mock ADES client methods
    mock_ades_api.create.return_value = True
    mock_ades_api.update.return_value = False
    mock_ades_api.delete.return_value = True

    # Call the function
    interpret_message(mock_message, ades_url)

    # Assert that the appropriate methods were called
    mock_s3_client.copy_object.assert_any_call(
        CopySource={"Bucket": "test-bucket", "Key": "workspace1/workflow1.access-policy.json"},
        Bucket="test-bucket",
        Key="deployed/workspace1/workflow1.access-policy.json",
    )
    mock_s3_client.copy_object.assert_any_call(
        CopySource={"Bucket": "test-bucket", "Key": "workspace1/workflow1.cwl"},
        Bucket="test-bucket",
        Key="deployed/workspace1/workflow1.cwl",
    )
    assert mock_s3_client.copy_object.call_count == 2

    # Policy not deleted as workflow wasn't deleted first
    assert mock_s3_client.delete_object.call_count == 0


@mock.patch("workflow_ingester.__main__.get_s3_client")
@mock.patch("workflow_ingester.__main__.AdesApiClient")
def test_policy_files_delete(MockAdesApiClient, MockGetS3Client):
    # Create mock instances
    mock_ades_api = MockAdesApiClient.return_value
    mock_s3_client = MockGetS3Client.return_value

    # Define mock message
    mock_message = json.dumps(
        {
            "added_keys": [],
            "updated_keys": [],
            "deleted_keys": [
                "workspace1/workflow1.cwl",
                "workspace1/test-workflow.access-policy.json",
            ],
            "bucket_name": "test-bucket",
        }
    )

    ades_url = "http://test-ades-url"

    # Mock S3 client methods
    mock_s3_client.get_object.side_effect = [
        {"Body": mock.Mock(read=lambda: b"$graph:\n  - id: test-workflow")},
        {"id": "test-workflow"},
    ]
    mock_s3_client.delete_object.return_value = None

    # Mock ADES client methods
    mock_ades_api.delete.return_value = True

    # Call the function
    interpret_message(mock_message, ades_url)

    # Assert that the appropriate methods were called
    mock_s3_client.delete_object.assert_any_call(
        Bucket="test-bucket", Key="deployed/workspace1/workflow1.cwl"
    )
    mock_s3_client.delete_object.assert_any_call(
        Bucket="test-bucket", Key="deployed/workspace1/test-workflow.access-policy.json"
    )


@mock.patch("workflow_ingester.__main__.interpret_message")
@mock.patch("workflow_ingester.__main__.logger")
def test_main(mock_logger, mock_interpret_message):
    consumer = mock.Mock()
    mock_message_1 = mock.Mock()
    mock_message_1.data.return_value = (
        b'{"added_keys": [], "updated_keys": [], "deleted_keys": [], "spec": {"aws": {"s3": '
        b'{"buckets": [{"path": "workspace/", "name": "bucket-name"}]}}}, "event": "update"}'
    )
    consumer.receive.side_effect = [mock_message_1, Exception("Stop loop")]
    ades_url = "http://test-ades-url"

    try:
        main(consumer, ades_url)
    except Exception as e:
        assert str(e) == "Stop loop"

    # Assert that the consumer's receive method was called
    assert consumer.receive.call_count == 2

    # Assert that interpret_message was called with the correct arguments
    mock_interpret_message.assert_any_call(
        mock_message_1.data.return_value.decode("utf-8"), ades_url, 0
    )

    # Assert that the consumer's acknowledge method was called with the mock messages
    consumer.acknowledge.assert_any_call(mock_message_1)
