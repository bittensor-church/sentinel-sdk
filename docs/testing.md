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

All factories extend `polyfactory.ModelFactory` and generate valid, fully-populated Pydantic models with random data. Override any field by passing keyword arguments to `.build()`.

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
