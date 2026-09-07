# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the
upcoming release can be found in [changelog.d](changelog.d).

<!-- towncrier release notes start -->

## [0.2.7](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.2.7) - 2026-09-07

### Removed

- `sentinel runtime info` no longer reports the impl name/version, authoring version, transaction version or state version. The v11 SDK exposes no block-pinned equivalent of the `state_getRuntimeVersion` RPC, so only the spec name and spec version (read from `System.LastRuntimeUpgrade`) remain.

### Changed

- Migrated to bittensor SDK v11 (`bittensor>=11.1,<12`), which is a ground-up rewrite of the SDK: `bittensor.core.*` no longer exists, and `Metagraph` is now a neuron-list dataclass rather than a set of tensor columns.

  Providers now return `sentinel.v1.providers.metagraph.SubnetMetagraph`, a provider-neutral model, instead of the SDK's own metagraph type. `BlockchainProvider.get_subnet_hyperparams` returns a plain dict, and weight and bond matrices are sparse `{source_uid: {target_uid: value}}` maps rather than dense arrays. `DividendsExtractor` now takes a `BlockchainProvider` rather than a raw `Subtensor`.

  `numpy` is now declared explicitly; it used to arrive as a transitive dependency of bittensor v10.
- `BittensorProvider` resolves block hashes to block numbers internally, since the v11 SDK addresses blocks by number. Hashes passed to `get_events`, `get_extrinsics` and `get_extrinsic_status` must come from `get_block_hash` on the same provider instance; an unrecognised hash now raises `ValueError` rather than silently reporting an empty block.

### Added

- `sentinel.v1.testing` ships `NeuronRecordFactory` and `SubnetMetagraphFactory` for the provider-neutral metagraph models, with reproducible seeding, bounded scores and stakes, and sequential neuron UIDs. `build_full()` supplies matching weight and bond matrices, including empty subnets, while `build_with_roles()` creates validators bonding to miners for dividend extraction tests. ([#metagraph-factories](https://github.com/bittensor-church/sentinel-sdk/issues/metagraph-factories))


## [0.2.6](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.2.6) - 2026-08-03

### Added

- `BlockchainProvider` gained `get_block_timestamp`, `get_subnet_emission_enabled`, and
  `get_all_subnets_netuids` (the last was previously only on `BittensorProvider`).
  `BittensorProvider` implements all three; `PylonProvider` raises `NotImplementedError`.
  `FakeBlockchainProvider` gained matching `with_block_timestamp`,
  `with_subnet_emission_enabled`, and `with_subnet_netuids` builders.
  `get_block_timestamp` returns None rather than 1970-01-01 when a node answers
  `Timestamp.Now` with the storage default for a block outside its state window.


## [0.2.5](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.2.5) - 2026-07-29

No significant changes.


## [0.2.4](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.2.4) - 2026-06-08

No significant changes.


## [0.2.3](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.2.3) - 2026-05-05

No significant changes.


## [0.2.3](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.2.3) - 2026-04-22

### Added

- `MetagraphExtractor` now populates `NeuronSnapshotBase.alpha_stake` (per-uid alpha stake in TAO) and `SubnetBase.alpha_out_emission` (subnet-wide alpha emission per block in TAO). Both default to `0.0` when the underlying metagraph object does not expose them. Required for downstream APY calculation.


## [0.2.2](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.2.2) - 2026-04-08

### Added

- `sentinel.v1.testing` module with DTO factories, extrinsic presets (hyperparameter, coldkey swap, register network), and `FakeBlockchainProvider` for writing tests without a live Bittensor node. Install with `pip install bittensor-sentinel[testing]`.


## [0.2.1](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.2.1) - 2026-04-03

- Pylon integration. Available in SDK and CLI


## [0.2.0](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.2.0) - 2026-02-18

No significant changes.


## [0.1.9](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.9) - 2026-01-29

No significant changes.


## [0.1.8](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.8) - 2026-01-28

No significant changes.


## [0.1.7](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.7) - 2026-01-25

No significant changes.


## [0.1.6](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.6) - 2026-01-12

No significant changes.


## [0.1.5](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.5) - 2026-01-12

No significant changes.


## [0.1.4](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.4) - 2025-12-19

No significant changes.


## [0.1.3](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.3) - 2025-12-19

No significant changes.


## [0.1.2](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.2) - 2025-12-19

No significant changes.


## [0.1.1](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.1) - 2025-12-19

No significant changes.


## [0.1.0](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.1.0) - 2025-12-10

No significant changes.


## [0.0.9](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.0.9) - 2025-12-09

No significant changes.


## [0.0.8](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.0.8) - 2025-12-05

No significant changes.


## [0.0.7](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.0.7) - 2025-12-04

No significant changes.


## [0.0.6](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.0.6) - 2025-12-04

No significant changes.


## [0.0.5](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.0.5) - 2025-12-01

No significant changes.


## [0.0.4](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.0.4) - 2025-11-28

No significant changes.


## [0.0.3](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.0.3) - 2025-11-28

No significant changes.


## [0.0.2](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.0.2) - 2025-11-28

No significant changes.


## [0.0.1](https://github.com/bittensor-church/sentinel-sdk/releases/tag/v0.0.1) - 2025-11-27

No significant changes.
