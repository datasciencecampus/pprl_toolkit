"""Hypothesis strategies for our embedder subpackage tests."""

import re
import string
from datetime import datetime

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from hypothesis import strategies as st
from scipy.linalg import qr

ALPHABET = string.ascii_letters + string.punctuation

NAMES = (
    "Fred Hogan O'Malley",
    "Angelina Guidone",
    "Zbyněk Liška",
    "Jolana Pešková",
    "Diane Elizabeth Davey-Hurst",
    "Vanessa Comencini",
    "Benito Montalcini",
    "Bettina Nitto",
    "Sandro Rubbia",
    "Alexandr Čech",
    "Adéla Strnadová",
    "Manuel Boaga",
    "Jamie Philip Smith",
    "Jordan Francis",
    "Melina Cantimori",
    "Maria Giulia Cattaneo",
    "Karel Strnad",
    "Silvie Čechová",
    "Markéta Sedláková",
    "Lucy Barrett-O'Reilly",
    "Tereza Kat'ya Blažková",
)


@st.composite
def st_mutated_names(draw, names=NAMES, mutagens=",-_+ ."):
    """Generate a name and its mutated form."""

    name = draw(st.sampled_from(names))
    mutated = "".join(draw(st.text(alphabet=" ", max_size=2)))
    for char in name:
        if char == " ":
            mutated += draw(st.text(alphabet=mutagens, min_size=1, max_size=3))
        else:
            mutated += char

    return name, mutated


@st.composite
def st_tokenized_names(draw, names=NAMES):
    """Generate a properly tokenized name."""

    name = draw(st.sampled_from(names))
    tokens = [f"_{word}_" for word in re.split(r"[\s-]", name)]

    return tokens


@st.composite
def st_names_series(draw, names=NAMES):
    """Generate a series of names."""

    names = draw(st.lists(st.sampled_from(names), min_size=1, max_size=100))

    return pd.Series(names)


@st.composite
def st_sexes_series(draw, options=("Male", "Female", "Non-binary", None)):
    """Generate a series of sexes."""

    sexes = draw(st.lists(st.sampled_from(options), min_size=1, max_size=100))

    return pd.Series(sexes)


@st.composite
def st_dobs_and_order_params(draw, years_range=100):
    """Generate a series of date strings and their order parameters."""

    dayfirst = draw(st.booleans())
    yearfirst = not dayfirst
    format_ = "%Y-%m-%d" if yearfirst else "%d/%m/%Y"

    max_value = datetime.today().date()
    min_value = max_value - relativedelta(years=years_range)
    st_dates = st.dates(min_value, max_value).map(lambda date: date.strftime(format_))
    dobs = draw(st.lists(st.one_of((st.just(None), st_dates)), min_size=1, max_size=10))

    return pd.Series(dobs), dayfirst, yearfirst, format_


@st.composite
def st_default_dobs(draw):
    """Generate a default DOB list."""

    date = draw(st.dates())

    return date.strftime("day<%d>_month<%m>_year<%Y>").split("_")


@st.composite
def st_fields_series(draw):
    """Generate a series of miscellaneous fields."""

    options = (
        st.text(alphabet=ALPHABET),
        st.integers(0, 10),
        st.lists(st.integers(0, 10), min_size=1, max_size=2),
        st.just(None),
    )
    fields = draw(st.lists(st.one_of(options), min_size=1, max_size=100))

    return pd.Series(fields)


@st.composite
def st_strings_series(draw):
    """Generate a series of strings."""

    options = (
        st.just(None),
        st.text(alphabet=ALPHABET, min_size=10, max_size=20),
    )
    strings = draw(st.lists(st.one_of(options), min_size=1, max_size=100))

    return pd.Series(strings)


@st.composite
def st_posdef_matrices(draw, bf_size=10):
    """Generate a square positive definite matrix."""

    rseed = draw(st.integers(2**10, 2**14))
    rng = np.random.default_rng(rseed)
    H = rng.normal(scale=2, size=(bf_size, bf_size))
    diag_values = rng.exponential(size=bf_size)
    Q, _ = qr(H)

    return Q.T @ np.diag(diag_values) @ Q


@st.composite
def st_bf_indices(draw, bf_size):
    """Generate a list of unique indices."""
    bf_indices = draw(st.lists(st.integers(min_value=0, max_value=bf_size - 1), max_size=bf_size))
    return list(set(bf_indices))


@st.composite
def st_matrix_and_indices(draw):
    """Generate a pos-def matrix and indices in the same size."""
    bf_size = draw(st.integers(2, 2**10))
    mat = draw(st_posdef_matrices(bf_size))
    bf_indices = draw(st_bf_indices(bf_size))
    return mat, bf_indices
