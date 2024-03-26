# `pprl`: Privacy-Preserving Record Linkage

## Installation

To install the package, clone this repository and install locally via pip:

```shell
git clone https://github.com/datasciencecampus/pprl_toolkit.git
cd pprl
python -m pip install .
```

> [!NOTE]
> If you are developing on (or contributing to) the project, install the package as editable with the `dev` optional dependencies:
>
> ```shell
> python -m pip install -e ".[dev]"
> ```

We encourage the use of pre-commit hooks.
To install these, run the following command from the root directory of the repository:

```shell
pre-commit install
```

## Running app.py

The app can be used to convert records to bloom filters and download them
locally without doing the following steps. However, if you want to upload the
data to Google Cloud Platfrom the following steps must be taken:

* Recieve the service account private key in a JSON file from the cloud admin and put the file in the the "secrets" folder.
* If you have received the file from the cloud admin skip this step. Otherwise if you are the cloud admin to create this file go to Service Acounts in the Google Cloud console. Click on the service account of interest e.g. "party-1-service-account-name..." or "party-2-service-account-name...". Click on keys, add key and create new key. Click on JSON and press create to download the service account private key.
* Edit the .env file to include the GOOGLE_APPLICATION_CREDENTIALS environmental variable as below:


    Ensure you insert your own absolute path to the root directory of the `pprl` project and the name of the service account private key JSON without the enclosing sharp brackets "<>". This absolute path be found entering "pwd" in a UNIX terminal or "cd" in a Windows terminal when in the root directory of the `pprl` project. Ensure the quotations wrap the key value.

```shell
    GOOGLE_APPLICATION_CREDENTIALS = "<insert absolute path to pprl>/secrets/<service account private key filename>"
```

## Configuring GCP

```shell
$ gcloud auth login
$ gcloud auth configure-docker <GCP region>-docker.pkg.dev
```
