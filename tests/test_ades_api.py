from json.decoder import JSONDecodeError
from unittest import mock

import pytest

from workflow_ingester.ades_api import AdesApiClient


@pytest.fixture
def ades_api_client():
    return AdesApiClient(base_url="http://example.com")


@mock.patch("requests.post")
@mock.patch("workflow_ingester.ades_api.logger")
def test_create_success(mock_logger, mock_post, ades_api_client):
    workspace = "test-workspace"
    workflow_id = "test-workflow"
    data = "test-data"

    mock_post.return_value.status_code = 201

    result = ades_api_client.create(workspace, workflow_id, data)

    assert result is True
    mock_post.assert_called_once_with(
        "http://example.com/test-workspace/ogc-api/processes",
        headers={"Content-Type": "application/cwl+yaml"},
        data=data,
    )
    mock_logger.error.assert_not_called()


@mock.patch("requests.post")
@mock.patch("workflow_ingester.ades_api.logger")
def test_create_failure(mock_logger, mock_post, ades_api_client):
    workspace = "test-workspace"
    workflow_id = "test-workflow"
    data = "test-data"

    mock_post.return_value.status_code = 400
    mock_post.return_value.json.return_value = {"error": "Bad Request"}

    result = ades_api_client.create(workspace, workflow_id, data)

    assert result is False
    mock_post.assert_called_once_with(
        "http://example.com/test-workspace/ogc-api/processes",
        headers={"Content-Type": "application/cwl+yaml"},
        data=data,
    )
    assert mock_logger.error.call_count == 3
    mock_logger.error.assert_any_call(
        "Failed to deploy workflow %s in workspace %s", "test-workflow", "test-workspace"
    )
    mock_logger.error.assert_any_call(
        "URL was %s", "http://example.com/test-workspace/ogc-api/processes"
    )
    mock_logger.error.assert_any_call("Response is %s", {"error": "Bad Request"})


@mock.patch("requests.post")
@mock.patch("workflow_ingester.ades_api.logger")
def test_create_failure_non_json_response(mock_logger, mock_post, ades_api_client):
    workspace = "test-workspace"
    workflow_id = "test-workflow"
    data = "test-data"

    mock_post.return_value.status_code = 400
    mock_post.return_value.json.side_effect = JSONDecodeError("Expecting value", "", 0)
    mock_post.return_value.text = "Non-JSON response"

    result = ades_api_client.create(workspace, workflow_id, data)

    assert result is False
    mock_post.assert_called_once_with(
        "http://example.com/test-workspace/ogc-api/processes",
        headers={"Content-Type": "application/cwl+yaml"},
        data=data,
    )
    assert mock_logger.error.call_count == 3
    mock_logger.error.assert_any_call(
        "Failed to deploy workflow %s in workspace %s", "test-workflow", "test-workspace"
    )
    mock_logger.error.assert_any_call(
        "URL was %s", "http://example.com/test-workspace/ogc-api/processes"
    )
    mock_logger.error.assert_any_call("Response is %s", "Non-JSON response")


@mock.patch("requests.put")
@mock.patch("workflow_ingester.ades_api.logger")
def test_update_success(mock_logger, mock_put, ades_api_client):
    workspace = "test-workspace"
    workflow_id = "test-workflow"
    data = "test-data"

    mock_put.return_value.status_code = 204

    result = ades_api_client.update(workspace, workflow_id, data)

    assert result is True
    mock_put.assert_called_once_with(
        "http://example.com/test-workspace/ogc-api/processes/test-workflow",
        headers={"Content-Type": "application/cwl+yaml"},
        data=data,
    )
    mock_logger.error.assert_not_called()


@mock.patch("requests.put")
@mock.patch("workflow_ingester.ades_api.logger")
def test_update_failure(mock_logger, mock_put, ades_api_client):
    workspace = "test-workspace"
    workflow_id = "test-workflow"
    data = "test-data"

    mock_put.return_value.status_code = 400
    mock_put.return_value.json.return_value = {"error": "Bad Request"}

    result = ades_api_client.update(workspace, workflow_id, data)

    assert result is False
    mock_put.assert_called_once_with(
        "http://example.com/test-workspace/ogc-api/processes/test-workflow",
        headers={"Content-Type": "application/cwl+yaml"},
        data=data,
    )
    assert mock_logger.error.call_count == 3
    mock_logger.error.assert_any_call(
        "Failed to update workflow %s in workspace %s", "test-workflow", "test-workspace"
    )
    mock_logger.error.assert_any_call(
        "URL was %s", "http://example.com/test-workspace/ogc-api/processes/test-workflow"
    )
    mock_logger.error.assert_any_call("Response is %s", {"error": "Bad Request"})


@mock.patch("requests.put")
@mock.patch("workflow_ingester.ades_api.logger")
def test_update_failure_non_json_response(mock_logger, mock_put, ades_api_client):
    workspace = "test-workspace"
    workflow_id = "test-workflow"
    data = "test-data"

    mock_put.return_value.status_code = 400
    mock_put.return_value.json.side_effect = JSONDecodeError("Expecting value", "", 0)
    mock_put.return_value.text = "Non-JSON response"

    result = ades_api_client.update(workspace, workflow_id, data)

    assert result is False
    mock_put.assert_called_once_with(
        "http://example.com/test-workspace/ogc-api/processes/test-workflow",
        headers={"Content-Type": "application/cwl+yaml"},
        data=data,
    )
    assert mock_logger.error.call_count == 3
    mock_logger.error.assert_any_call(
        "Failed to update workflow %s in workspace %s", "test-workflow", "test-workspace"
    )
    mock_logger.error.assert_any_call(
        "URL was %s", "http://example.com/test-workspace/ogc-api/processes/test-workflow"
    )
    mock_logger.error.assert_any_call("Response is %s", "Non-JSON response")


@mock.patch("requests.delete")
@mock.patch("workflow_ingester.ades_api.logger")
def test_delete_success(mock_logger, mock_delete, ades_api_client):
    workspace = "test-workspace"
    workflow_id = "test-workflow"

    mock_delete.return_value.status_code = 204

    result = ades_api_client.delete(workspace, workflow_id)

    assert result is True
    mock_delete.assert_called_once_with(
        "http://example.com/test-workspace/ogc-api/processes/test-workflow"
    )
    mock_logger.error.assert_not_called()


@mock.patch("requests.delete")
@mock.patch("workflow_ingester.ades_api.logger")
def test_delete_failure(mock_logger, mock_delete, ades_api_client):
    workspace = "test-workspace"
    workflow_id = "test-workflow"

    mock_delete.return_value.status_code = 400
    mock_delete.return_value.json.return_value = {"error": "Bad Request"}

    result = ades_api_client.delete(workspace, workflow_id)

    assert result is False
    mock_delete.assert_called_once_with(
        "http://example.com/test-workspace/ogc-api/processes/test-workflow"
    )
    assert mock_logger.error.call_count == 3
    mock_logger.error.assert_any_call(
        "Failed to delete workflow %s in workspace %s", "test-workflow", "test-workspace"
    )
    mock_logger.error.assert_any_call(
        "URL was %s", "http://example.com/test-workspace/ogc-api/processes/test-workflow"
    )
    mock_logger.error.assert_any_call("Response is %s", {"error": "Bad Request"})


@mock.patch("requests.delete")
@mock.patch("workflow_ingester.ades_api.logger")
def test_delete_failure_non_json_response(mock_logger, mock_delete, ades_api_client):
    workspace = "test-workspace"
    workflow_id = "test-workflow"

    mock_delete.return_value.status_code = 400
    mock_delete.return_value.json.side_effect = JSONDecodeError("Expecting value", "", 0)
    mock_delete.return_value.text = "Non-JSON response"

    result = ades_api_client.delete(workspace, workflow_id)

    assert result is False
    mock_delete.assert_called_once_with(
        "http://example.com/test-workspace/ogc-api/processes/test-workflow"
    )
    assert mock_logger.error.call_count == 3
    mock_logger.error.assert_any_call(
        "Failed to delete workflow %s in workspace %s", "test-workflow", "test-workspace"
    )
    mock_logger.error.assert_any_call(
        "URL was %s", "http://example.com/test-workspace/ogc-api/processes/test-workflow"
    )
    mock_logger.error.assert_any_call("Response is %s", "Non-JSON response")
