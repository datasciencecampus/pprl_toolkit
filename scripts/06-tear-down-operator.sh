#!/bin/bash
#
# Tears down all billable resources for the workload operator.

echo "Loading functions and environment variables..."
source common.sh

set_gcp_project $WORKLOAD_OPERATOR_PROJECT

echo "Deleting workload virtual machine..."
gcloud compute instances delete \
  projects/$WORKLOAD_OPERATOR_PROJECT/zones/$WORKLOAD_OPERATOR_PROJECT_ZONE/instances/pprl-cvm

delete_storage_bucket $ATTESTATION_BUCKET

delete_service_account $WORKLOAD_SERVICE_ACCOUNT_EMAIL
