

[This Google tutorial](https://cloud.google.com/confidential-computing/confidential-space/docs/create-your-first-confidential-space-environment)
provides a simple example to familiarise yourselves with the concepts and commands.

### Determining roles

There are four roles to fill in a data linkage project: two data-owning
parties, a workload author, and a workload operator. A workload is how we refer
to the linkage operation itself. These roles can be summarised as follows:

- A data-owning **party** is responsible for embedding and uploading their data
  to the cloud. They also download their results. There are typically two data-owning parties.
- The workload **author** audits and assures the source code of the server, and then builds and uploads the server as a Docker image.
- The workload **operator** sets up and runs the Confidential
  Space virtual machine, which uses the Docker image to perform the record linkage.

> [!NOTE]
> We have set up `pprl_toolkit` to allow any configuration of these roles among
> users. You could do it all yourself, split the workload roles between two
> data owning-parties, or use a third-party administrator to maintain the
> workload.

### Creating your projects

Once you have decided who will be filling which role(s), every member of your
linkage project will need to set up a GCP project. The names of these projects
will be used in file names and GCP storage buckets. As such, they need to be
descriptive and [globally unique](https://cloud.google.com/storage/docs/buckets#naming).

> [!TIP]
> It may be worth appending a hash of some sort to every project name to help
> ensure their uniqueness.

Each user will also need to have their Google Cloud administrator grant them
certain IAM roles on their project depending on which role(s) they are playing
in the linkage:

- **Data-owning party**:
  - Cloud KMS Admin (`roles/cloudkms.admin`)
  - IAM Workload Identity Pool Admin (`roles/iam.workloadIdentityPoolAdmin`)
  - Service Usage Admin (`roles/serviceusage.serviceUsageAdmin`)
  - Service Account Admin (`roles/iam.serviceAccountAdmin`)
  - Storage Admin (`roles/storage.admin`)
- **Workload author**:
  - Artifact Registry Administrator (`roles/artifactregistry.admin`)
- **Workload operator**:
  - Compute Admin (`roles/compute.admin`)
  - Security Admin (`roles/securityAdmin`)
  - Storage Admin (`roles/storage.admin`)

### Toolkit configuration

Now you've got your roles sorted out and projects set up, you (and all other
users) have to write down your project's configuration in an environment file
for `pprl_toolkit`. Make sure that everyone has installed `pprl_toolkit` first.

We have provided an example in `.env.example`. All you need to do is copy that
file to `.env` and fill in your project's details. Everyone in your project
should have identical environment files.

### Creating the other resources

The last step in setting your linkage project up is to create and configure all
the other resources on GCP. We have packaged up these steps into a series of
`bash` scripts, located in the `scripts/` directory. They should be executed in
order from the `scripts/` directory:

1. The data-owning parties set up a key encryption key, a bucket in which to
   store their encrypted data, data encryption key and results, a service
   account for accessing said bucket and key, and a workload identity pool to
   allow impersonations under stringent conditions:
   ```bash
   sh ./01-setup-party-resources.sh <name-of-party-project>
   ```
2. The workload operator sets up a bucket for the parties to put their
   (non-sensitive) attestation credentials, and a service account for running
   the workload:
   ```bash
   sh ./02-setup-workload-operator.sh
   ```
3. The workload author sets up an Artifact Registry on GCP, creates a Docker
   image and uploads that image to their registry:
   ```bash
   sh ./03-setup-workload-author.sh
   ```
4. The data-owning parties authorise the workload operator's service account to
   use the workload identity pool to impersonate their service account in a
   Confidential Space:
   ```bash
   sh ./04-authorise-workload.sh <name-of-party-project>
   ```

### Processing and uploading the datasets

> [!IMPORTANT]
> This section only applies to data-owning parties. The workload author is
> finished now, and the workload operator should wait for this section to be
> completed before moving on to the next section.

Now that all the cloud infrastructure has been set up, we are ready to start
the first step in doing the actual linkage. Much like the toy example above,
that is to make a Bloom filter embedding of each dataset.

For users who prefer a graphical user interface, we have included a Flask app
to handle the processing and uploading of data behind the scenes. This app will
also be used to download the results once the linkage has completed.

To launch the app, run the following in your terminal:

```bash
python -m flask --app src/pprl/app run
```

You should now be able to find the app in your browser of choice at
[127.0.0.1:5000](http://127.0.0.1:5000).

Once you have worked through the selection, processing, and GCP upload portions
of the app, you will be at a holding page. This page can be updated by clicking
the button, and when your results are ready you will be taken to another page
where you can download them.

### Running the linkage

> [!IMPORTANT]
> This section only applies to the workload operator.

Once the data-owning parties have uploaded their processed data, you are able
to begin the linkage. To do so, run the `05-run-workload.sh` bash script from
`scripts/`:

```bash
cd /path/to/pprl_toolkit/scripts
sh ./05-run-workload.sh
```

You can follow the progress of the workload from the Logs Explorer on GCP. Once
it is complete, the data-owning parties will be able to download their results.
