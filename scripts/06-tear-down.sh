#!/bin/bash
set -e
set -o pipefail

# This script sets up the server architecture for linkage on GCP

## Load in our environment variables
echo "Loading environment variables..."
export $(grep "^PROJECT" .env.admin | xargs -0)
export PROJECT_PARTIES=($PROJECT_PARTY_1 $PROJECT_PARTY_2)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_NAME --format "value(projectNumber)")
export SERVICE_DOMAIN=$PROJECT_NAME.iam.gserviceaccount.com
export KEYRINGS_LOCATION=projects/$PROJECT_NAME/locations/$PROJECT_REGION/keyRings

# Delete compute instance
echo "Y" | gcloud compute instances delete projects/$PROJECT_NAME/zones/$PROJECT_REGION/instances/pprl-tee

# (option) Delete docker repo and any images
echo "Y" | gcloud artifacts repositories delete pprl-repo --location=$PROJECT_REGION

# Delete service accounts

# Delete keys

# (option) Delete storage buckets


# Delete workload identity pools and any attestation verifiers
