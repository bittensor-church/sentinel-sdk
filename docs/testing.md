# Testing utilities

Sentinel SDK ships a `sentinel.v1.testing` module with factories and a fake provider so you can write fast, deterministic tests without hitting a real Bittensor node.

## Installation

Install with the `testing` extra:

```bash
pip install bittensor-sentinel[testing]
```

This pulls in [polyfactory](https://github.com/litestar-org/polyfactory) as an additional dependency.

## Quick start

```python
from sentinel.v1.testing import (
    ExtrinsicDTOFactory,
    NeuronSnapshotFullFactory,
    FullSubnetSnapshotFactory,
    SubnetMetagraphFactory,
    FakeBlockchainProvider,
)

# Generate a realistic extrinsic in one line
extrinsic = ExtrinsicDTOFactory.build()

# Generate a full neuron snapshot with all relations
neuron = NeuronSnapshotFullFactory.build()
print(neuron.neuron.hotkey.hotkey)  # SS58 hotkey address
print(neuron.mechanisms[0].dividend)  # mechanism metrics

# Generate a complete subnet metagraph snapshot
snapshot = FullSubnetSnapshotFactory.build()
print(snapshot.subnet.netuid)
print(len(snapshot.neurons))  # 3 neurons by default

# Generate what a provider returns: a chain-side metagraph
metagraph = SubnetMetagraphFactory.build_full(neuron_count=8)
print(metagraph.weights_sum(0))  # 1.0

# Set up a fake provider with chain state
provider = (
    FakeBlockchainProvider()
    .with_block(100, "0xabc")
    .with_extrinsics("0xabc", FakeBlockchainProvider.create_mock_extrinsics(5))
    .with_events("0xabc", FakeBlockchainProvider.create_mock_events(3))
    .with_hyperparams(100, 1, {"tempo": 360, "rho": 10})
)
```

## Factories

Most factories extend `polyfactory.ModelFactory` and generate valid, fully-populated Pydantic models with random data. The provider metagraph factories extend `polyfactory.DataclassFactory`, since the models they build are dataclasses. Override any field by passing keyword arguments to `.build()`.

### Extrinsic & Event factories

| Factory | Generates | Notes |
|---|---|---|
| `CallArgDTOFactory` | `CallArgDTO` | Single call argument |
| `CallDTOFactory` | `CallDTO` | Call with 3 nested `CallArgDTO`s |
| `ExtrinsicDTOFactory` | `ExtrinsicDTO` | Extrinsic with nested `CallDTO` |
| `EventDataDTOFactory` | `EventDataDTO` | Event data payload |
| `EventDTOFactory` | `EventDTO` | Event with nested `EventDataDTO` |
| `HyperparametersDTOFactory` | `HyperparametersDTO` | Subnet hyperparameters |
| `SubnetInfoDTOFactory` | `SubnetInfoDTO` | Subnet info |
| `HyperparamCallDTOFactory` | `CallDTO` | Hyperparameter-setting call (`AdminUtils` module) |
| `HyperparamExtrinsicDTOFactory` | `ExtrinsicDTO` | Hyperparameter-setting extrinsic with `build_for_function()` helper |
| `AnnounceColdkeySwapCallDTOFactory` | `CallDTO` | Announce swap call (`SubtensorModule.announce_coldkey_swap`) |
| `AnnounceColdkeySwapExtrinsicDTOFactory` | `ExtrinsicDTO` | Announce swap extrinsic with `build_for_hash()` helper |
| `ColdkeySwapCallDTOFactory` | `CallDTO` | Coldkey swap call (`SubtensorModule.swap_coldkey_announced`) |
| `ColdkeySwapExtrinsicDTOFactory` | `ExtrinsicDTO` | Coldkey swap extrinsic with `build_for_coldkey()` helper |
| `DisputeColdkeySwapCallDTOFactory` | `CallDTO` | Coldkey swap dispute call (`SubtensorModule.dispute_coldkey_swap`) |
| `DisputeColdkeySwapExtrinsicDTOFactory` | `ExtrinsicDTO` | Coldkey swap dispute extrinsic (no call args) |
| `ClearColdkeySwapCallDTOFactory` | `CallDTO` | Clear swap announcement call (`SubtensorModule.clear_coldkey_swap_announcement`) |
| `ClearColdkeySwapExtrinsicDTOFactory` | `ExtrinsicDTO` | Clear swap announcement extrinsic (no call args) |
| `ResetColdkeySwapCallDTOFactory` | `CallDTO` | Reset coldkey swap call (`SubtensorModule.reset_coldkey_swap`) |
| `ResetColdkeySwapExtrinsicDTOFactory` | `ExtrinsicDTO` | Reset coldkey swap extrinsic with `build_for_coldkey()` helper |
| `RegisterNetworkCallDTOFactory` | `CallDTO` | Register network call (`SubtensorModule.register_network`) |
| `RegisterNetworkExtrinsicDTOFactory` | `ExtrinsicDTO` | Register network extrinsic with `build_for_hotkey()` helper |
| `RegisterNetworkWithIdentityCallDTOFactory` | `CallDTO` | Register with identity call (`SubtensorModule.register_network_with_identity`) |
| `RegisterNetworkWithIdentityExtrinsicDTOFactory` | `ExtrinsicDTO` | Register with identity extrinsic with `build_for_hotkey(subnet_name=)` helper |

### Key factories

| Factory | Generates | Notes |
|---|---|---|
| `ColdkeyFactory` | `Coldkey` | Cold wallet address with DB fields |
| `HotkeyFactory` | `Hotkey` | Hot wallet address with DB fields |
| `HotkeyWithColdkeyFactory` | `HotkeyWithColdkey` | Hotkey with embedded coldkey relation |
| `EVMKeyFactory` | `EVMKey` | EVM-compatible address |

### Block & Subnet factories

| Factory | Generates | Notes |
|---|---|---|
| `BlockFactory` | `Block` | Block number + timestamp |
| `SubnetFactory` | `Subnet` | Subnet with DB fields |
| `SubnetWithOwnerFactory` | `SubnetWithOwner` | Subnet with owner hotkey relation |

### Neuron factories

| Factory | Generates | Notes |
|---|---|---|
| `NeuronFactory` | `Neuron` | Neuron with uid, hotkey_id, subnet_id |
| `NeuronWithRelationsFactory` | `NeuronWithRelations` | Neuron with embedded hotkey, coldkey, subnet |

### Snapshot factories

| Factory | Generates | Notes |
|---|---|---|
| `MechanismMetricsFactory` | `MechanismMetrics` | Per-mechanism metrics (incentive, dividend, consensus) |
| `NeuronSnapshotFactory` | `NeuronSnapshot` | Neuron state at a specific block |
| `NeuronSnapshotWithMechanismsFactory` | `NeuronSnapshotWithMechanisms` | Snapshot with 1 mechanism metrics entry |
| `NeuronSnapshotFullFactory` | `NeuronSnapshotFull` | Complete snapshot with neuron relations, block, and mechanisms |

### Tensor factories

| Factory | Generates | Notes |
|---|---|---|
| `WeightFactory` | `Weight` | Validator-to-miner weight record |
| `BondFactory` | `Bond` | Validator-to-miner bond record |
| `CollateralFactory` | `Collateral` | Collateral record |

### Tracking & Aggregate factories

| Factory | Generates | Notes |
|---|---|---|
| `MetagraphDumpFactory` | `MetagraphDump` | Metagraph dump tracking record |
| `EmissionRecordFactory` | `EmissionRecord` | Computed emission record |
| `SubnetSnapshotSummaryFactory` | `SubnetSnapshotSummary` | Subnet summary with counts and total stake |
| `FullSubnetSnapshotFactory` | `FullSubnetSnapshot` | Complete metagraph dump with 3 neurons, subnet, block |

### Provider metagraph factories

These build `sentinel.v1.providers.metagraph` models — what a `BlockchainProvider` returns, and therefore what the extractors consume. Scores stay in 0..1 and stakes are non-negative amounts in whole-token units. Registration and last-update blocks default to 0, so they do not postdate a historical snapshot; override them to test immunity and activity boundaries. Generated addresses have the SS58 prefix, alphabet, and length but **no valid checksum**; supply real addresses when testing address validation.

| Factory | Generates | Notes |
|---|---|---|
| `NeuronRecordFactory` | `NeuronRecord` | One metagraph row, with `batch_with_uids()` for sequential uids |
| `SubnetMetagraphFactory` | `SubnetMetagraph` | Lite metagraph with 3 neurons; `build_full()` adds tensors; `build_with_roles()` creates validators and miners for dividend tests |

`SubnetMetagraph.neuron()` looks a neuron up by list position, so a graph's neurons must carry uids matching their index. `NeuronRecordFactory.batch_with_uids(n)` numbers them accordingly; plain `batch(n)` randomizes uids and breaks that invariant. The graph factory rejects non-sequential, duplicate, or out-of-order uids rather than generating mismatched tensors.

`build_full()` generates synthetic equal-weight connections between every pair of distinct neurons. Neurons default to having no validator permit, so use `build_with_roles()` for a nonzero Yuma3 dividend scenario: it gives validators positive equal stake, miners equal incentive and zero stake, and connects only validators to miners. Override `weights` or `bonds` to exercise asymmetric calculations or missing data. These are test presets, not simulations of chain consensus.

```python
from sentinel.v1.testing import NeuronRecordFactory, SubnetMetagraphFactory

# A lite metagraph: 3 neurons with uids 0..2, no weights or bonds
metagraph = SubnetMetagraphFactory.build(netuid=7, block=100)

# A full one: weights and bonds keyed by its own uids, dividends by its own hotkeys
metagraph = SubnetMetagraphFactory.build_full(neuron_count=64)

# Empty and single-neuron subnets are supported
empty = SubnetMetagraphFactory.build_full(neurons=[])
single = SubnetMetagraphFactory.build_full(neuron_count=1)  # empty tensor rows

# A populated dividend scenario: two validators bonding to three miners
metagraph = SubnetMetagraphFactory.build_with_roles(validator_count=2, miner_count=3)

# Model a provider that cannot return bonds, or a fetched but empty matrix
missing_bonds = SubnetMetagraphFactory.build_full(bonds=None)
empty_bonds = SubnetMetagraphFactory.build_full(bonds={})

# Bring your own neurons, e.g. two validators and two miners
neurons = [
    *NeuronRecordFactory.batch_with_uids(2, validator_permit=True, total_stake=100.0),
    *NeuronRecordFactory.batch_with_uids(2, start=2, incentive=0.5),
]
metagraph = SubnetMetagraphFactory.build_full(neurons=neurons)

# Reproduce all random fields, including nested neurons and dividend maps
SubnetMetagraphFactory.seed_random(42)
first = SubnetMetagraphFactory.build_full()
SubnetMetagraphFactory.seed_random(42)
assert SubnetMetagraphFactory.build_full() == first
```

## Common patterns

```python
from sentinel.v1.testing import (
    ExtrinsicDTOFactory,
    NeuronSnapshotFullFactory,
    FullSubnetSnapshotFactory,
    HyperparamExtrinsicDTOFactory,
    ColdkeySwapExtrinsicDTOFactory,
    WeightFactory,
)

# Override fields
ext = ExtrinsicDTOFactory.build(block_number=500, extrinsic_hash="0xdeadbeef")

# Build a batch
neurons = NeuronSnapshotFullFactory.batch(20)

# Build a hyperparameter-changing extrinsic for a specific function
ext = HyperparamExtrinsicDTOFactory.build_for_function(
    "sudo_set_tempo",
    netuid=1,
    tempo=360,
)

# Build a metagraph snapshot with specific neuron count
snapshot = FullSubnetSnapshotFactory.build(
    neurons=NeuronSnapshotFullFactory.batch(64),
)

# Build a coldkey swap extrinsic
ext = ColdkeySwapExtrinsicDTOFactory.build()

# Build one for a specific destination coldkey
ext = ColdkeySwapExtrinsicDTOFactory.build_for_coldkey(
    "5CHuuWaMucXwaLqjM4jsvAp9NvrxMpavus1dBMsCEiqvRtNU",
)

# Build a coldkey swap dispute extrinsic
from sentinel.v1.testing import DisputeColdkeySwapExtrinsicDTOFactory
ext = DisputeColdkeySwapExtrinsicDTOFactory.build()

# Build tensor data for a specific block
weights = WeightFactory.batch(10, block_number=100)

# Feed a chain-side metagraph to an extractor through the fake provider
from sentinel.v1.testing import FakeBlockchainProvider, SubnetMetagraphFactory
provider = FakeBlockchainProvider().with_metagraph(
    SubnetMetagraphFactory.build_full(netuid=1, block=100),
    block_number=100,
)
```

## FakeBlockchainProvider

`FakeBlockchainProvider` is an in-memory implementation of the `BlockchainProvider` abstract base class. It can be used as a drop-in replacement anywhere `BlockchainProvider` is expected.

### Fluent builder API

Configure chain state using the `with_*` methods, which return `self` for chaining:

```python
from sentinel.v1.testing import FakeBlockchainProvider

provider = (
    FakeBlockchainProvider()
    .with_block(100, "0xabc")
    .with_block(101, "0xdef")
    .with_extrinsics("0xabc", [{"call": {"call_module": "System"}}])
    .with_events("0xabc", [{"event_id": "Transfer"}])
    .with_hyperparams(100, 1, {"tempo": 360})
)

# Use it like a real provider
assert provider.get_block_hash(100) == "0xabc"
assert provider.get_subnet_hyperparams(100, 1) == {"tempo": 360}
```

| Method | Description |
|---|---|
| `with_block(block_number, block_hash)` | Register a block number to hash mapping |
| `with_events(block_hash, events)` | Register events for a block hash |
| `with_extrinsics(block_hash, extrinsics)` | Register extrinsics for a block hash |
| `with_hyperparams(block_number, netuid, hyperparams)` | Register hyperparameters for a block/subnet pair |
| `with_block_timestamp(block_number, timestamp)` | Register a chain timestamp for a block; blocks left out read back as `None` |
| `with_metagraph(metagraph, block_number)` | Register a `SubnetMetagraph` at a block, keyed by its own netuid and mechid |
| `with_subnet_netuids(netuids)` | Set which subnets are registered on the chain |
| `with_subnet_emission_enabled(block_number, emission_enabled)` | Register the `SubnetEmissionEnabled` map at a block |

### Static helpers

Generate mock data using the built-in factories:

```python
events = FakeBlockchainProvider.create_mock_events(count=3)
extrinsics = FakeBlockchainProvider.create_mock_extrinsics(count=5)

# With overrides
extrinsics = FakeBlockchainProvider.create_mock_extrinsics(
    count=2,
    block_number=42,
)
```

### Full example with pytest

```python
import pytest
from sentinel.v1.testing import FakeBlockchainProvider
from sentinel.v1.services.sentinel import sentinel_service


@pytest.fixture
def provider():
    block_hash = "0xabc123"
    return (
        FakeBlockchainProvider()
        .with_block(100, block_hash)
        .with_extrinsics(
            block_hash,
            FakeBlockchainProvider.create_mock_extrinsics(5),
        )
        .with_events(
            block_hash,
            FakeBlockchainProvider.create_mock_events(3),
        )
    )


def test_block_ingestion(provider):
    service = sentinel_service(provider)
    block = service.ingest_block(100)
    assert len(block.extrinsics) == 5
    assert len(block.events) == 3
```
