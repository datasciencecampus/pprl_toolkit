#!/bin/bash
#
# Tears down all billable resources for the workload operator.

echo "Loading functions and environment variables..."
source common.sh

set_gcp_project $WORKLOAD_AUTHOR_PROJECT

delete_artifact_repository $ARTIFACT_REPOSITORY $WORKLOAD_AUTHOR_PROJECT_REGION
