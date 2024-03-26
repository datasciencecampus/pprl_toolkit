#!/bin/bash
#
# Creates a service account for the workload operator.

echo "Loading functions and environment variables..."
source common.sh

set_gcp_project $WORKLOAD_OPERATOR_PROJECT

echo "Enabling APIs for workload operator on $WORKLOAD_OPERATOR_PROJECT..."
gcloud services enable \
  compute.googleapis.com \
  confidentialcomputing.googleapis.com \
  logging.googleapis.com

echo "Creating attestion bucket for $WORKLOAD_OPERATOR_PROJECT..."
create_storage_bucket $ATTESTATION_BUCKET

echo "Granting parties the rights to access $ATTESTATION_BUCKET..."
grant_attestation_bucket_rights $PARTY_1_PROJECT_EMAIL $ATTESTATION_BUCKET
grant_attestation_bucket_rights $PARTY_2_PROJECT_EMAIL $ATTESTATION_BUCKET

echo "Creating workload service account $WORKLOAD_SERVICE_ACCOUNT under $WORKLOAD_OPERATOR_PROJECT..."
create_service_account $WORKLOAD_SERVICE_ACCOUNT

echo "Granting roles/storage.admin role for $ATTESTATION_BUCKET to service account $WORKLOAD_SERVICE_ACCOUNT..."
if ! gcloud storage buckets add-iam-policy-binding gs://$ATTESTATION_BUCKET \
  --member=serviceAccount:$WORKLOAD_SERVICE_ACCOUNT_EMAIL \
  --role=roles/storage.admin; then
  err "Failed to grant roles/storage.admin role for $ATTESTATION_BUCKET to service account $WORKLOAD_SERVICE_ACCOUNT."
fi

echo "Granting roles/iam.serviceAccountUser role to workload operator..."
if ! gcloud iam service-accounts add-iam-policy-binding $WORKLOAD_SERVICE_ACCOUNT_EMAIL \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/iam.serviceAccountUser"; then
  err "Failed to grant role to workload operator $WORKLOAD_OPERATOR_USER under $WORKLOAD_OPERATOR_PROJECT."
fi

echo "Granting roles/confidentialcomputing.workloadUser to service account $WORKLOAD_SERVICE_ACCOUNT..."
if ! gcloud projects add-iam-policy-binding $WORKLOAD_OPERATOR_PROJECT \
  --member="serviceAccount:$WORKLOAD_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/confidentialcomputing.workloadUser"; then
  err "Failed to grant roles/confidentialcomputing.workloadUser to service-account $WORKLOAD_SERVICE_ACCOUNT."
fi

echo "Granting roles/logging.logWriter to service account $WORKLOAD_SERVICE_ACCOUNT..."
if ! gcloud projects add-iam-policy-binding $WORKLOAD_OPERATOR_PROJECT \
  --member="serviceAccount:$WORKLOAD_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/logging.logWriter"; then
  err "Failed to grant roles/logging.logWriter to service account $WORKLOAD_SERVICE_ACCOUNT."
fi
