# Sentinel sdk
&nbsp;[![Continuous Integration](https://github.com/bittensor-church/sentinel/workflows/Continuous%20Integration/badge.svg)](https://github.com/bittensor-church/sentinel/actions?query=workflow%3A%22Continuous+Integration%22)&nbsp;[![License](https://img.shields.io/pypi/l/bittensor-sentinel.svg?label=License)](https://pypi.python.org/pypi/bittensor-sentinel)&nbsp;[![python versions](https://img.shields.io/pypi/pyversions/bittensor-sentinel.svg?label=python%20versions)](https://pypi.python.org/pypi/bittensor-sentinel)&nbsp;[![PyPI version](https://img.shields.io/pypi/v/bittensor-sentinel.svg?label=PyPI%20version)](https://pypi.python.org/pypi/bittensor-sentinel)

Sentinel is a blockchain data extraction and monitoring tool designed to work with the Bittensor network.

Features:
- Extract extrinsics, events, and hyperparameters from Bittensor blockchain.
- Provides both a Python library and a command-line interface (CLI) for ease of use.

## Installation

```bash
pip install bittensor-sentinel
```

## Usage

> [!IMPORTANT]
> This package uses [ApiVer](#versioning), make sure to import `sentinel.v1`.

### As a library

```python
from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel.v1.services.extractors.extrinsics import get_hyperparam_extrinsics
from sentinel.v1.services.sentinel import sentinel_service

provider = bittensor_provider()
service = sentinel_service(provider)
block = service.ingest_block(resolved_block)
for extrinsic in block.extrinsics:
    print(extrinsic)
```

## Pylon integration

Sentinel supports [Pylon](https://github.com/bittensor-church/bittensor-pylon/) as an alternative blockchain provider. Pylon is a caching proxy for the Bittensor network that provides faster neuron and validator queries.

### Setup

1. Run a Pylon instance (see [Pylon documentation](https://github.com/bittensor-church/bittensor-pylon/)).
2. Set the `PYLON_URL` environment variable (optional — defaults to `http://localhost:8000`):
   ```bash
   export PYLON_URL="http://your-pylon-instance:8090"
   export PYLON_OPEN_ACCESS_TOKEN="your-token"  # optional, only if Pylon requires authentication
   ```

### As a library

Use `PylonProvider` as a drop-in replacement for `BittensorProvider`:

```python
from sentinel.v1.providers.pylon import pylon_provider

# Uses PYLON_URL env var, or pass url directly
provider = pylon_provider(url="http://localhost:8090")

# Fetch metagraph (constructed from Pylon neuron data, always lite mode)
metagraph = provider.get_metagraph(netuid=1, block_number=100000, lite=True)

# Pylon-specific methods (not in the base BlockchainProvider interface)
neurons = provider.get_neurons(netuid=1, block_number=100000)
validators = provider.get_validators(netuid=1, block_number=100000)
latest = provider.get_latest_neurons(netuid=1)
```

> [!NOTE]
> PylonProvider does not support block events, extrinsics listing, or subnet hyperparameters.
> These methods raise `NotImplementedError`. Use `BittensorProvider` for full chain access.

### CLI

Use the `--provider pylon` flag with subnet commands:

```bash
# Query metagraph via Pylon
sentinel subnet --netuid 1 --provider pylon metagraph

# With a custom Pylon URL
sentinel subnet --netuid 1 --provider pylon --network http://my-pylon:8090 metagraph

# JSON output
sentinel subnet --netuid 1 --provider pylon -f json metagraph
```

### CLI (general)

```
$ sentinel --help


Usage: sentinel [OPTIONS] COMMAND [ARGS]...

Sentinel CLI - Blockchain data extraction and monitoring tool.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format              -f      [table|json]  Output format. [default: table]  │
│ --install-completion                        Install completion for the       │
│                                             current shell.                   │
│ --show-completion                           Show completion for the current  │
│                                             shell, to copy it or customize   │
│                                             the installation.                │
│ --help                                      Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ extrinsics    Read extrinsics from a blockchain block.                       │
│ events        Read events from a blockchain block.                           │
│ hyperparams   Read hyperparameters for a subnet at a specific block.         │
│ block         Block-related commands.                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
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
