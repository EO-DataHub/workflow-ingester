# Changelog

## v0.1.0 (09-10-2024)
- Initial commit of the workflow-ingester
  - Code to monitor a Pulsar topic, when triggered this repo performs S3 actions and deploys/undeploys workflows from the user's workspace
  - Code handles both workflow definitions as well as workflow policy files
- Including tests and image build workflows