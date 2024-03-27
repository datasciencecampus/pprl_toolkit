#!/bin/bash
#
# Tears down all billable resources for the data-owning party.

echo "Loading functions and environment variables..."
source common.sh

export PROJECT_NAME=${1}
export PROJECT_KEY_VERSION=${2}
if [ ! $PROJECT_KEY_VERSION ]; then
do
  export PROJECT_KEY_VERSION=1
done

set_gcp_project $PROJECT_NAME

delete_storage_bucket $PROJECT_NAME-bucket

destroy_kms_key_version \
  $PROJECT_NAME-akek $PROJECT_NAME-akek-kr $PROJECT_LOCATION $PROJECT_KEY_VERSION

delete_workload_identity_pool $PROJECT_NAME-wip $PROJECT_LOCATION

delete_service_account $PROJECT_NAME-sa@$PROJECT_NAME.iam.gserviceaccount.com
