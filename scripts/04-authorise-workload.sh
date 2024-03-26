#!/bin/bash
#
# Authorises the workload to use the identity pool.

echo "Loading functions and environment variables..."
source common.sh

export PROJECT_NAME=${1}
export PROJECT_WORKLOAD_IDENTITY_POOL=$PROJECT_NAME-wip
export PROJECT_WIP_PROVIDER=$PROJECT_WORKLOAD_IDENTITY_POOL-provider
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_NAME --format="value(projectNumber)")
export PROJECT_SERVICE_ACCOUNT_EMAIL=$PROJECT_NAME-sa@$PROJECT_NAME.iam.gserviceaccount.com

export OPERATION=${2}
if [ ! $OPERATION ]; then
  export OPERATION=create
fi

set_gcp_project $PROJECT_NAME

echo "Creating provider for $PROJECT_WORKLOAD_IDENTITY_POOL authorising $WORKLOAD_IMAGE_REFERENCE..."
gcloud iam workload-identity-pools providers ${OPERATION}-oidc $PROJECT_WIP_PROVIDER \
  --location=$PROJECT_LOCATION \
  --workload-identity-pool="$PROJECT_WORKLOAD_IDENTITY_POOL" \
  --issuer-uri="https://confidentialcomputing.googleapis.com/" \
  --allowed-audiences="https://sts.googleapis.com" \
  --attribute-mapping="google.subject='assertion.sub'" \
  --attribute-condition="assertion.swname == 'CONFIDENTIAL_SPACE' &&
    'STABLE' in assertion.submods.confidential_space.support_attributes &&
    assertion.submods.container.image_reference == '$WORKLOAD_IMAGE_REFERENCE:$WORKLOAD_IMAGE_TAG' &&
    '$WORKLOAD_SERVICE_ACCOUNT_EMAIL' in assertion.google_service_accounts"

echo "Creating attestation credentials file for $WORKLOAD_SERVICE_ACCOUNT..."
gcloud iam workload-identity-pools create-cred-config \
  projects/$PROJECT_NUMBER/locations/$PROJECT_LOCATION/workloadIdentityPools/$PROJECT_WORKLOAD_IDENTITY_POOL/providers/$PROJECT_WIP_PROVIDER \
  --service-account=$PROJECT_SERVICE_ACCOUNT_EMAIL \
  --credential-source-file="/run/container_launcher/attestation_verifier_claims_token" \
  --output-file=../secrets/$PROJECT_NAME-attestation-credentials.json

echo "Copying attestation credentials for $PROJECT_NAME to $ATTESTATION_BUCKET..."
if ! gsutil cp ../secrets/$PROJECT_NAME-attestation-credentials.json gs://$ATTESTATION_BUCKET/; then
  err "Failed to upload the attestation credentials for $PROJECT_NAME to $ATTESTATION_BUCKET."
fi
