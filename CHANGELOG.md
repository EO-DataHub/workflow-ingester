# Changelog

## v0.1.0 (10-10-2024)
Initial commit of the workflow-ingester
- Added code to ingest workflows into the Workflow Runner, via HTTP, from S3
- Copying files, workflows and policies, to a `deployed` bucket directory
- Triggered by Pulsar messaging
- Logging to record processing and failure
- Unit tests