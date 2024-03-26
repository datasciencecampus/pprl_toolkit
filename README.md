# `pprl_toolkit`: a toolkit for privacy-preserving record linkage

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

Let us consider a small example where we want to link two excerpts of data on
bands. In this scenario, we are looking at some toy data on the members of the
psychedelic-rock trio, [Khruangbin](https://en.wikipedia.org/wiki/Khruangbin).

### Loading the data

First, we load our data into `pandas.DataFrame` objects. Here, the first
records align, but the other two records should be swapped to have an aligned
matching. We will use the toolkit to identify these matches.

```python
>>> import pandas as pd
>>>
>>> df1 = pd.DataFrame(
...     {
...         "first_name": ["Laura", "Mark", "DJ"],
...         "last_name": ["Ochoa", "Speer", "Johnson"],
...         "gender": ["f", "m", "m"],
...         "instrument": ["bass", "guitar", "drums"],
...         "vocals_ever": [True, True, True],
...     }
... )
>>> df2 = pd.DataFrame(
...     {
...         "name": ["Laura 'Leezy' Lee Ochoa", "Donald J Johnson", "Marc Spear"],
...         "sex": ["female", "male", "male"],
...         "main_instrument": ["bass guitar", "percussion", "electric guitar"],
...         "vocals": ["yes", "sometimes", "sometimes"],
...     }
... )

```

> [!NOTE]
> These datasets don't have the same column names or follow the same encodings.
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
the filter and the number of hashes. By default, these are `2**10` and `2`,
respectively.

Once we've decided, we can create our `Embedder` instance and use it to embed
our data with their column specifications.

```python
>>> from pprl.embedder.embedder import Embedder
>>>
>>> embedder = Embedder(factory, bf_size=2**10, num_hashes=2)
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
SimilarityArray([[0.70133435, 0.01848053, 0.04622502],
                 [0.06659271, 0.11581371, 0.55522526],
                 [0.06584864, 0.66803136, 0.11935249]])

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
