#!/bin/bash
#
# Creates artifact repository and workload image, then uploads the image.

echo "Loading functions and environment variables..."
source common.sh

set_gcp_project $WORKLOAD_AUTHOR_PROJECT

echo "Enabling APIs for workload author on $WORKLOAD_AUTHOR_PROJECT..."
gcloud services enable artifactregistry.googleapis.com

create_artifact_repository $ARTIFACT_REPOSITORY $WORKLOAD_AUTHOR_REGION

gcloud auth configure-docker $WORKLOAD_AUTHOR_PROJECT_REGION-docker.pkg.dev

echo "Building the workload Docker image..."
cd ..
docker build . -t $WORKLOAD_IMAGE_REFERENCE
cd scripts

echo "Pushing the workload Docker image to artifact registry $ARTIFACT_REPOSITORY..."
docker push $WORKLOAD_IMAGE_REFERENCE:$WORKLOAD_IMAGE_TAG

echo "Granting roles/artifactregistry.reader role to workload service account $WORKLOAD_SERVICE_ACCOUNT..."
gcloud artifacts repositories add-iam-policy-binding $ARTIFACT_REPOSITORY \
    --project=$WORKLOAD_AUTHOR_PROJECT \
    --role=roles/artifactregistry.reader \
    --location=$WORKLOAD_AUTHOR_PROJECT_REGION \
    --member="serviceAccount:$WORKLOAD_SERVICE_ACCOUNT_EMAIL"
