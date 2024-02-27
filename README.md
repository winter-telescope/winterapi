# winterapi
API interactions for WINTER

[![Coverage Status](https://coveralls.io/repos/github/winter-telescope/winterapi/badge.svg?branch=tests)](https://coveralls.io/github/winter-telescope/winterapi?branch=tests)
[![CI](https://github.com/winter-telescope/winterapi/actions/workflows/continuous_integration.yml/badge.svg)](https://github.com/winter-telescope/winterapi/actions/workflows/continuous_integration.yml) 
[![PyPI version](https://badge.fury.io/py/winterapi.svg)](https://badge.fury.io/py/winterapi)

## Installation

We advise you to install the package in a virtual environment or conda environment.
You will need python 3.10 or later to use this package.

### Install from pypi
```bash
pip install winterapi
```

### Install from source
```bash
git clone git@github.com:winter-telescope/winterapi.git
cd winterapi
pip install --editable ".[dev]"
pre-commit install
```

## Updating the package

You will need to occasionally update the package to get the latest features and bug fixes. 
Sometimes the server will require a newer version of the package to interact with it, 
and you will receive a warning when using winterapi.
You can update by running the following command:

### Updating for pypi
```bash
pip install --upgrade winterapi
```

or 

### Updating from source
```bash
cd winterapi
git pull
pip install --editable ".[dev]"
pre-commit install
```

## Using winterapi

You can find example usage under `notebooks/` directory in this repository.
The notebooks are numbered, and walk you through setting up credentials,
triggering a ToO, checking on the status of a ToO, and downloading images after
observations are complete.

## Problems?

The first port of call if you have any problems is to download the latest
version of the package. You might even get a warning when using the package that your
version is out of date. If you are still having problems after updating, 
you could also try re-entering your credentials. 

If you are still having problems, please open a Github Issue and we will
try to help you as soon as possible.
