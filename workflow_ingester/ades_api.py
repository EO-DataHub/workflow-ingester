import logging
from json import JSONDecodeError

import requests

logger = logging.getLogger(__name__)


class AdesApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def create(self, workspace: str, workflow_id: str, data: str):
        logger.info("Deploying workflow %s to workspace %s", workflow_id, workspace)
        headers = {"Content-Type": "application/cwl+yaml"}
        response = requests.post(
            f"{self.base_url}/{workspace}/ogc-api/processes", headers=headers, data=data
        )
        if response.status_code != 201:
            logger.error("Failed to deploy workflow %s in workspace %s", workflow_id, workspace)
            logger.error("URL was %s", f"{self.base_url}/{workspace}/ogc-api/processes")
            try:
                logger.error("Response is %s", response.json())
            except JSONDecodeError:
                logger.error("Response is %s", response.text)
            return False
        return True

    def update(self, workspace: str, workflow_id: str, data: str):
        logger.info("Updating workflow %s in workspace %s", workflow_id, workspace)
        headers = {"Content-Type": "application/cwl+yaml"}
        response = requests.put(
            f"{self.base_url}/{workspace}/ogc-api/processes/{workflow_id}",
            headers=headers,
            data=data,
        )
        if response.status_code != 204:
            logger.error("Failed to update workflow %s in workspace %s", workflow_id, workspace)
            logger.error(
                "URL was %s", f"{self.base_url}/{workspace}/ogc-api/processes/{workflow_id}"
            )
            try:
                logger.error("Response is %s", response.json())
            except JSONDecodeError:
                logger.error("Response is %s", response.text)
            return False
        return True

    def delete(self, workspace: str, workflow_id: str):
        logger.info("Deleting workflow %s from workspace %s", workflow_id, workspace)
        response = requests.delete(f"{self.base_url}/{workspace}/ogc-api/processes/{workflow_id}")
        if response.status_code != 204:
            logger.error("Failed to delete workflow %s in workspace %s", workflow_id, workspace)
            logger.error(
                "URL was %s", f"{self.base_url}/{workspace}/ogc-api/processes/{workflow_id}"
            )
            try:
                logger.error("Response is %s", response.json())
            except JSONDecodeError:
                logger.error("Response is %s", response.text)
            return False
        return True
