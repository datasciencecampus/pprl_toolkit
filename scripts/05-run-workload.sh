#!/bin/bash
#
# Sets the workload running on GCP.

echo "Loading functions and environment variables..."
source common.sh

set_gcp_project $WORKLOAD_OPERATOR_PROJECT

echo "Setting up confidential VM..."
gcloud compute instances create pprl-cvm \
  --confidential-compute \
  --shielded-secure-boot \
  --maintenance-policy=TERMINATE \
  --scopes=cloud-platform \
  --zone=$WORKLOAD_OPERATOR_PROJECT_ZONE \
  --image-project=confidential-space-images \
  --image-family=confidential-space \
  --service-account=$WORKLOAD_SERVICE_ACCOUNT_EMAIL \
    --metadata "^~^tee-image-reference=$WORKLOAD_IMAGE_REFERENCE:$WORKLOAD_IMAGE_TAG~tee-restart-policy=Never"
