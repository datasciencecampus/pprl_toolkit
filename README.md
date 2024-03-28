![ONS and DSC logos](https://github.com/datasciencecampus/awesome-campus/blob/master/ons_dsc_logo.png)

# `pprl_toolkit`: a toolkit for privacy-preserving record linkage


The Privacy Preserving Record Linkage (PPRL) toolkit has been developed by data scientists at the Data Science Campus of the UK Office for National Statistics. This project has benefitted from earlier collaborations with colleagues at NHS England.

The toolkit has been designed for a situation where two organisations (perhaps in different jurisdictions) want to link their datasets at record level, to enrich the information they contain, but neither party is able to send sensitive personal identifiers to the other. Building on [previous ONS research](https://www.gov.uk/government/publications/joined-up-data-in-government-the-future-of-data-linking-methods/privacy-preserving-record-linkage-in-the-context-of-a-national-statistics-institute), the toolkit implements a well-known privacy-preserving linkage method in a new way to improve performance, and wraps it in a secure cloud architecture to demonstrate the potential of a layered approach.

The two parts of the toolkit are:

* a Python package for privacy-preserving record linkage with Bloom filters and hash embeddings, that can be used locally with no cloud set-up
* Instructions, scripts and resources to run record linkage in a cloud-based secure enclave. This part of the toolkit requires you to set up a Google Cloud account with billing

We're publishing the repo as a prototype and teaching tool. Please feel free to download, adapt and experiment with it in compliance with the open-source license. You can submit issues here. However, as this is an experimental repo, the development team cannot commit to maintaining the repo or responding to issues.

## Installation

To install the package from source, you must clone the repository before
installing locally via `pip`:

```shell
git clone https://github.com/datasciencecampus/pprl_toolkit.git
cd pprl_toolkit
python -m pip install .
```

### Installing as a developer

If you are developing on (or contributing to) the project, install the package
as editable with the `dev` optional dependencies:

```shell
python -m pip install -e ".[dev]"
```

We also encourage the use of pre-commit hooks for development work. These hooks
help us ensure the security of our code base and a consistent code style.

To install these, run the following command from the root directory of the
repository:

```shell
pre-commit install
```

## Getting started

The Python package implements both the Bloom filter linkage method ([Schnell et al., 2009](https://bmcmedinformdecismak.biomedcentral.com/articles/10.1186/1472-6947-9-41)), and can also implement pretrained Hash embeddings ([Miranda et al., 2022](https://arxiv.org/abs/2212.09255)), if a suitable large, pre-matched corpus of data is available.

Let us consider a small example where we want to link two excerpts of data on
bands. In this scenario, we are looking at some toy data on the members of a
fictional, German rock trio called "Verknüpfung". In this example we will see how to use untrained Bloom filters to match data.

### Loading the data

First, we load our data into `pandas.DataFrame` objects. Here, the first
records align, but the other two records should be swapped to have an aligned
matching. We will use the toolkit to identify these matches.

```python
>>> import pandas as pd
>>>
>>> df1 = pd.DataFrame(
...     {
...         "first_name": ["Laura", "Kaspar", "Grete"],
...         "last_name": ["Daten", "Gorman", "Knopf"],
...         "gender": ["f", "m", "f"],
...         "instrument": ["bass", "guitar", "drums"],
...         "vocals_ever": [True, True, True],
...     }
... )
>>> df2 = pd.DataFrame(
...     {
...         "name": ["Laura Datten", "Greta Knopf", "Casper Goreman"],
...         "sex": ["female", "female", "male"],
...         "main_instrument": ["bass guitar", "percussion", "electric guitar"],
...         "vocals": ["yes", "sometimes", "sometimes"],
...     }
... )

```

> [!NOTE]
> These datasets don't have the same column names or follow the same encodings,
> and there are several spelling mistakes in the names of the band members.
>
> Thankfully, the `pprl_toolkit` is flexible enough to handle this!

### Creating and assigning a feature factory

The next step is to decide how to process each of the columns in our datasets.

To do this, we define a feature factory that maps column types to feature
generation functions, and a column specification for each dataset mapping our
columns to column types in the factory.

```python
>>> from pprl.embedder import features
>>>
>>> factory = dict(
...     name=features.gen_name_features,
...     sex=features.gen_sex_features,
...     misc=features.gen_misc_features,
... )
>>> spec1 = dict(
...     first_name="name",
...     last_name="name",
...     gender="sex",
...     instrument="misc",
...     vocals_ever="misc",
... )
>>> spec2 = dict(name="name", sex="sex", main_instrument="misc", vocals="misc")

```

### Embedding the data

With our specifications sorted out, we can get to creating our Bloom filter
embedding. Before doing so, we need to decide on two parameters: the size of
the filter and the number of hashes. By default, these are `1024` and `2`,
respectively.

Once we've decided, we can create our `Embedder` instance and use it to embed
our data with their column specifications.

```python
>>> from pprl.embedder.embedder import Embedder
>>>
>>> embedder = Embedder(factory, bf_size=1024, num_hashes=2)
>>> edf1 = embedder.embed(df1, colspec=spec1, update_thresholds=True)
>>> edf2 = embedder.embed(df2, colspec=spec2, update_thresholds=True)

```

If we take a look at one of these embedded datasets, we can see that it has a
whole bunch of new columns. There is a `_features` column for each of the
original columns containing their pre-embedding string features. Then there are
three additional columns: `bf_indices`, `bf_norms` and `thresholds`.

```python
>>> edf1.columns
Index(['first_name', 'last_name', 'gender', 'instrument', 'vocals_ever',
       'first_name_features', 'last_name_features', 'gender_features',
       'instrument_features', 'vocals_ever_features', 'all_features',
       'bf_indices', 'bf_norms', 'thresholds'],
      dtype='object')

```

<!-- TODO: What do these columns actually describe? -->

### Performing the linkage

We can now perform the linkage by comparing these Bloom filter embeddings. We
use the Soft Cosine Measure to calculate record-wise similarity and an adapted
Hungarian algorithm to match the records based on those similarities.

```python
>>> similarities = embedder.compare(edf1, edf2)
>>> similarities
SimilarityArray([[0.86017213, 0.14285716, 0.12803688],
                 [0.13216962, 0.13483999, 0.50067019],
                 [0.12126782, 0.76292716, 0.09240265]])

```

This `SimilarityArray` object is an augmented `numpy.ndarray` that can perform
our matching. The matching itself has a number of parameters that allow you to
control how similar two embedded records must be to be matched. In this case,
let's say that two records can only be matched if their pairwise similarity is
at least `0.5`.

```python
>>> matching = similarities.match(abs_cutoff=0.5)
>>> matching
(array([0, 1, 2]), array([0, 2, 1]))

```

So, all three of the records in each dataset were matched correctly. Excellent!


## Working in the cloud


![A diagram of the PPRL cloud architecture, with the secure enclave and key management services](https://github.com/datasciencecampus/pprl_toolkit/blob/main/assets/pprl_cloud_diagram.png?raw=true)

The toolkit is configured to work on Google Cloud Platform (GCP) which requires Google Cloud accounts with billing set up. In particular, `pprl_toolkit`'s cloud functionality is built on
top of a GCP Confidential Space. This setting means that nobody ever has direct
access to each other's data, and the datasets to be linked are only ever
brought together in a secure environment.

Have a read through [this tutorial](https://cloud.google.com/confidential-computing/confidential-space/docs/create-your-first-confidential-space-environment)
if you would like to get to grips with how it all works on the inside.

### Determining roles

There are four roles to fill in a data linkage project: two data-owning
parties, a workload author, and a workload operator. A workload is how we refer
to the linkage operation itself. These roles can be summarised as follows:

- A data-owning **party** is responsible for embedding and uploading their data
  to the cloud. They also download their results.
- The workload **author** creates and uploads a Docker image to a GCP Artifact
  Registry.
- The workload **operator** runs the uploaded Docker image on a Confidential
  Space virtual machine.

> [!NOTE]
> We have set up `pprl_toolkit` to allow any configuration of these roles among
> users. You could do it all yourself, split the workload roles between two
> data owning-parties, or use a third-party administrator to maintain the
> workload.

### Creating your projects

Once you have decided who will be filling which role(s), every member of your
linkage project will need to set up a GCP project. The names of these projects
will be used in file names and GCP storage buckets. As such, they need to be
descriptive and [unique](https://cloud.google.com/storage/docs/buckets#naming).

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

## Building the documentation

This package is accompanied by documentation which includes tutorials and API
reference materials. These are available on [GitHub Pages](https://datasciencecampus.github.io/pprl_toolkit).

If you would like to build the documentation yourself, you will need to install
[Quarto](https://quarto.org/docs/get-started/). After that, install the `docs`
optional dependencies for the toolkit:

```bash
python -m pip install ".[docs]"
```

Now you can build, render, and view the documentation yourself. First, build
the API reference material:

```bash
python -m quartodoc build
```

This will create a bunch of files under `docs/reference/`. You can render the
documentation itself with the following command, opening a local version of the
site in your browser:

```bash
quarto preview
```
