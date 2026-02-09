# Workflow Ingester

A repository defining an image that listens to a Pulsar topic and upon receiving a message updates the specified files in S3 and then sends requests to the ADES in order to Deploy, Update or Delete the workflow from the specified user's workspace. The following steps are performed:
- Copies/updates/deletes workflow file (`.cwl`) to a new `deployed` directory in the S3 bucket
- Copies/updates/deletes workflow policy file (`.access-policy.json`) to a new `deployed` directory in the S3 bucket
- Deploys the workflow to the ADES under the specified workspace

Note, this application currently doesn't support deleting workflows from a workspace, as the file will be deleted, meaning the workflow ID cannot be identified.

This `deployed` repository is the used by the `workflow-runner-api` to identify the access policy for the given workflow.

# Development of this component

## Getting started

### Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/).

### Install via makefile

```commandline
make setup
```

This will install dependencies via `uv sync` and set up `pre-commit` hooks.

It's safe and fast to run `make setup` repeatedly as it will only update these things if
they have changed.

After `make setup` you can run `make pre-commit` to run pre-commit checks on staged changes and
`make pre-commit-all` to run them on all files. This replicates the linter checks that
run from GitHub actions.

## Building and testing

This component uses `pytest` tests and `ruff` for linting and formatting.

A number of `make` targets are defined:
* `make test`: run tests continuously (watch mode)
* `make testonce`: run tests once
* `make format`: lint and reformat code
* `make check`: run all checks (ruff, pyright, validate-pyproject)
* `make dockerbuild`: build a `latest` Docker image (use `make dockerbuild VERSION=1.2.3` for a release image)
* `make dockerpush`: push a `latest` Docker image (again, you can add `VERSION=1.2.3`) - normally this should be done
  only via the build system and its GitHub actions.

## Managing requirements

Runtime dependencies are specified in `pyproject.toml` under `[project.dependencies]`, and development
dependencies under `[dependency-groups]`. After changing them:

* Run `uv sync` to update the lockfile and install dependencies.
* Run `make check` and `make testonce` to verify everything works.
* Commit `pyproject.toml` and `uv.lock`.

## Releasing

Ensure that `make format` and `make check` produce no errors and no further changes to code formatting before
continuing.

Releases tagged `latest` and targeted at development environments can be created from the `main` branch. Releases for
installation in non-development environments should be created from a Git tag named using semantic versioning. For
example, using

* `git tag v1.2.3`
* `git push --tags`

Docker images will be built automatically by GitHub Actions after pushing to the EO-DataHub repos.
