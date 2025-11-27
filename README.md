# sentinel
&nbsp;[![Continuous Integration](https://github.com/bittensor-church/sentinel/workflows/Continuous%20Integration/badge.svg)](https://github.com/bittensor-church/sentinel/actions?query=workflow%3A%22Continuous+Integration%22)&nbsp;[![License](https://img.shields.io/pypi/l/sentinel.svg?label=License)](https://pypi.python.org/pypi/sentinel)&nbsp;[![python versions](https://img.shields.io/pypi/pyversions/sentinel.svg?label=python%20versions)](https://pypi.python.org/pypi/sentinel)&nbsp;[![PyPI version](https://img.shields.io/pypi/v/sentinel.svg?label=PyPI%20version)](https://pypi.python.org/pypi/sentinel)

## Usage

> [!IMPORTANT]
> This package uses [ApiVer](#versioning), make sure to import `sentinel.v1`.


## Installation

```bash
pip install bittensor-sentinel
```


## Versioning

This package uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
TL;DR you are safe to use [compatible release version specifier](https://packaging.python.org/en/latest/specifications/version-specifiers/#compatible-release) `~=MAJOR.MINOR` in your `pyproject.toml` or `requirements.txt`.

Additionally, this package uses [ApiVer](https://www.youtube.com/watch?v=FgcoAKchPjk) to further reduce the risk of breaking changes.
This means, the public API of this package is explicitly versioned, e.g. `sentinel.v1`, and will not change in a backwards-incompatible way even when `sentinel.v2` is released.

Internal packages, i.e. prefixed by `sentinel._` do not share these guarantees and may change in a backwards-incompatible way at any time even in patch releases.


## Development


Pre-requisites:
- [uv](https://docs.astral.sh/uv/)
- [nox](https://nox.thea.codes/en/stable/)
- [docker](https://www.docker.com/) and [docker compose plugin](https://docs.docker.com/compose/)


Ideally, you should run `nox -t format lint` before every commit to ensure that the code is properly formatted and linted.
Before submitting a PR, make sure that tests pass as well, you can do so using:
```
nox -t check # equivalent to `nox -t format lint test`
```

If you wish to install dependencies into `.venv` so your IDE can pick them up, you can do so using:
```
uv sync --all-extras --dev
```

### Release process

Run `nox -s make_release -- X.Y.Z` where `X.Y.Z` is the version you're releasing and follow the printed instructions.
