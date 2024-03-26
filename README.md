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
