#!/bin/bash
#
# Sets up the cloud resources for a data-owning party.

echo "Loading functions and environment variables..."
source common.sh

export PROJECT_NAME=$1
export PROJECT_BUCKET=$PROJECT_NAME-bucket
export PROJECT_KEYRING=$PROJECT_NAME-akek-kr
export PROJECT_KEY=$PROJECT_NAME-akek
export PROJECT_SERVICE_ACCOUNT=$PROJECT_NAME-sa
export PROJECT_SERVICE_ACCOUNT_DOMAIN=$PROJECT_NAME.iam.gserviceaccount.com
export PROJECT_SERVICE_ACCOUNT_EMAIL=$PROJECT_SERVICE_ACCOUNT@$PROJECT_SERVICE_ACCOUNT_DOMAIN
export PROJECT_WORKLOAD_IDENTITY_POOL=$PROJECT_NAME-wip
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_NAME --format="value(projectNumber)")

set_gcp_project $PROJECT_NAME

echo "Enabling APIs for data owners on $PROJECT_NAME..."
gcloud services enable cloudkms.googleapis.com iamcredentials.googleapis.com

echo "Creating bucket for $PROJECT_NAME..."
create_storage_bucket $PROJECT_BUCKET

echo "Creating keyring for $PROJECT_NAME..."
create_kms_keyring $PROJECT_KEYRING $PROJECT_LOCATION

echo "Creating key encryption key on $PROJECT_KEYRING..."
create_kms_encryption_key $PROJECT_KEY $PROJECT_KEYRING global

echo "Creating service account for $PROJECT_NAME..."
create_service_account $PROJECT_SERVICE_ACCOUNT

echo "Granting roles/storage.admin role to $PROJECT_SERVICE_ACCOUNT on $PROJECT_BUCKET..."
gcloud storage buckets add-iam-policy-binding gs://$PROJECT_BUCKET \
  --member=serviceAccount:$PROJECT_SERVICE_ACCOUNT_EMAIL \
  --role=roles/storage.admin

echo "Granting KMS roles to the service account $PROJECT_SERVICE_ACCOUNT..."
gcloud kms keys add-iam-policy-binding \
  $PROJECT_KEY \
  --keyring=$PROJECT_KEYRING \
  --location=$PROJECT_LOCATION \
  --member=serviceAccount:$PROJECT_SERVICE_ACCOUNT_EMAIL \
  --role=roles/cloudkms.publicKeyViewer
gcloud kms keys add-iam-policy-binding \
  $PROJECT_KEY \
  --keyring=$PROJECT_KEYRING \
  --location=$PROJECT_LOCATION \
  --member=serviceAccount:$PROJECT_SERVICE_ACCOUNT_EMAIL \
  --role=roles/cloudkms.cryptoKeyDecrypter

echo "Creating workload identity pool for $PROJECT_NAME..."
create_workload_identity_pool $PROJECT_WORKLOAD_IDENTITY_POOL $PROJECT_LOCATION

echo "Attaching service account $PROJECT_SERVICE_ACCOUNT to workload identity pool $PROJECT_WORKLOAD_IDENTITY_POOL..."
gcloud iam service-accounts add-iam-policy-binding $PROJECT_SERVICE_ACCOUNT_EMAIL \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/$PROJECT_LOCATION/workloadIdentityPools/$PROJECT_WORKLOAD_IDENTITY_POOL/*" \
  --role=roles/iam.workloadIdentityUser
