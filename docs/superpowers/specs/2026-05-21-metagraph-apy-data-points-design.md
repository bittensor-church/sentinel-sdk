# Metagraph APY Data Points — Design

**Date:** 2026-05-21
**Repo:** sentinel-sdk
**Status:** Approved design, pending spec review

## Problem

Validator/staker APY in the dTAO era is computed from per-epoch data points the
SDK does not currently surface. The reference formula lives in sentinel-tower's
`docs/apy-formula-2.md`; the critical inputs are:

- `alpha_earned` — net dividends per hotkey this epoch, from `AlphaDividendsPerSubnet`
  (metagraph index 71). Already **net** of subnet-owner cut and validator take.
- `alpha_staked` — the per-validator stake base.
- `tempo` — epoch length, to annualize.
- `moving_price` — alpha→TAO price (for optional TAO-denominated views).

Today the sentinel metagraph extractor surfaces `alpha_stake` (current per-uid
stake) but **not** `alpha_dividends_per_hotkey`, `tao_dividends_per_hotkey`,
`moving_price`, or `tempo`. The `MechanismMetrics.dividend` field is the
normalized u16 dividend *share* (sums to 1), not the rao alpha amount — it is not
`alpha_earned`.

### Feasibility (confirmed)

The underlying bittensor v10 `Metagraph` object already carries these via the
MetagraphInfo mixin:

- `metagraph.alpha_dividends_per_hotkey: list[tuple[str, float]]` (TAO/alpha float)
- `metagraph.tao_dividends_per_hotkey: list[tuple[str, float]]`
- `metagraph.pool.moving_price: float`
- `metagraph.tempo: int` (also `metagraph.hparams.tempo`)

`_apply_extra_info` (which applies this mixin) runs in `Metagraph.sync()` **outside**
the `if not lite` branch (`bittensor/core/metagraph.py:1447`), so the data is present
in **both** lite and non-lite syncs — including sentinel-tower's live (lite) sync path.

For historical blocks the data comes from the MetagraphInfo runtime API, so an
**archive node can serve it** (state-retention permitting) — historical backfill is
not limited to going-forward collection.

## Scope

In scope (this spec):
1. Add the four data points to the metagraph DTO.
2. Populate them in the metagraph extractor (defensively).
3. A pure, importable shortcut-formula helper (single-epoch annualized APY).
4. A `sentinel subnet apy` CLI command that renders an APY verification table,
   plus exposing the new fields in the existing `metagraph --output json`.
5. Unit tests for the helper and the extractor mapping.

Out of scope (explicit follow-up):
- Persisting these fields in sentinel-tower (`NeuronSnapshot` / `Subnet` model
  fields + migration + sync-service wiring).
- Windowed/compounded APY across a real block range (multi-epoch sampling).
- `owner_cut` (`SubnetOwnerCut/65535`) and `hotkey_take` (`Delegates/65535`):
  not needed for net APY (already applied inside `alpha_dividends_per_hotkey`),
  and they require extra storage queries. Deferred until the gross-reconstruction
  path is actually needed.

## Key decisions

- **Approach C:** raw data points on the DTO (no baked-in calculation) + a separate,
  opt-in shortcut-formula helper + the CLI command. The DTO stays calc-free because
  the APY formula may be adjusted by the client.
- **Denomination:** alpha-denominated APY is the headline. For a *single epoch* the
  price cancels within the epoch (`alpha_earned·p / alpha_staked·p`), so a separate
  TAO-APY column would be identical unless we modeled price drift across the
  annualization window (a forward assumption a verification command should not make).
  `tao_dividends` and `moving_price` are still exposed as data points so a client can
  build TAO views; the CLI shows `moving_price` as context, not a duplicate APY column.
- **Stake base:** use the metagraph's current `alpha_stake` tensor (already extracted,
  no extra RPC), accepting a slight approximation vs `TotalHotkeyAlphaLastEpoch`.
- **CLI shape:** `sentinel subnet -u <netuid> apy`, matching the existing shared
  `subnet` callback convention (netuid is the `-u/--netuid` option). Not positional.

## Components

### 1. DTO — `src/sentinel/v1/services/extractors/metagraph/dto.py`

`NeuronSnapshotBase` gains:
- `alpha_dividends: float = 0.0` — net dividends for this neuron's hotkey this epoch
  (alpha, TAO float). 0.0 when the underlying metagraph does not expose it.
- `tao_dividends: float = 0.0` — TAO-denominated equivalent.

The subnet DTO (`SubnetBase`/`SubnetWithOwner`, whichever the extractor builds — the
field is added on the shared base so both the top-level `SubnetWithOwner` and the
per-neuron embedded `Subnet` carry it) gains:
- `moving_price: float = 0.0` — alpha→TAO moving price.
- `tempo: int = 0` — epoch length in blocks.

All defaulted so existing callers and historical blocks remain valid.

### 2. Extractor — `src/sentinel/v1/services/extractors/metagraph/extractor.py`

- New helper `_build_dividends_maps(metagraph) -> tuple[dict[str, float], dict[str, float]]`
  building `{hotkey: alpha_div}` and `{hotkey: tao_div}` from
  `getattr(metagraph, "alpha_dividends_per_hotkey", [])` and
  `getattr(metagraph, "tao_dividends_per_hotkey", [])`.
- `_build_neuron_snapshots` builds the maps once and passes them down;
  `_build_single_neuron_snapshot` looks up by the neuron's hotkey (default 0.0 if absent)
  and sets `alpha_dividends` / `tao_dividends`.
- `_build_subnet` and the per-neuron `subnet_dto` set:
  - `moving_price`: `getattr(getattr(metagraph, "pool", None), "moving_price", 0.0)`
  - `tempo`: `getattr(metagraph, "tempo", None)` or `hparams.tempo`, else 0.
- A small `_read_moving_price` / `_read_tempo` static helper mirroring the existing
  `_read_alpha_out_emission` pattern, with a `logger.warning` when the source is missing.

### 3. Shortcut helper — new `src/sentinel/v1/services/apy.py`

Pure functions, no chain access:

```python
SECONDS_PER_YEAR = 31_557_600  # 365.25 days
BLOCK_TIME_SECONDS = 12

def epochs_per_year(tempo: int) -> float:
    return SECONDS_PER_YEAR / ((tempo + 1) * BLOCK_TIME_SECONDS)

def single_epoch_apy(alpha_earned: float, alpha_staked: float, tempo: int) -> float:
    """Shortcut: annualize ONE epoch's return by compounding.

    Not a substitute for true windowed APY (which samples many epochs).
    Returns a percentage. Guards alpha_staked <= 0 -> 0.0.
    """
    if alpha_staked <= 0:
        return 0.0
    r_epoch = alpha_earned / alpha_staked
    return ((1 + r_epoch) ** epochs_per_year(tempo) - 1) * 100
```

Docstring states explicitly this is the shortcut single-epoch annualization, and that
`alpha_earned` from index 71 is already net (no owner-cut/take correction).

### 4. CLI — `src/sentinel_cli/commands/subnet.py`

New `@subnet.command()` named `apy`:
- Reads netuid/block/network/mechid/provider from the shared `ctx.obj` (existing pattern).
- Resolves the block, builds the `Subnet`/`FullSubnetSnapshot` via the existing path.
- Builds a table: `UID | Hotkey | Alpha Staked | Alpha Earned | r_epoch | APY%`,
  restricted to validators (`is_validator`), sorted by APY desc.
- Header lines: block, subnet, `moving_price`, `tempo`, `epochs_per_year`.
- `--output json`: emits per-validator data points (`uid`, `hotkey`, `alpha_staked`,
  `alpha_earned`, `tao_dividends`, `tempo`, `moving_price`, `apy`).
- Uses `single_epoch_apy` for the APY column.
- Reuses `HOTKEY_DISPLAY_LENGTH`, `_print_elapsed_time`, `_handle_pylon_error`,
  `StateDiscardedError` handling already in the module.

Also extend the existing `metagraph` command's JSON branch to include
`alpha_dividends` / `tao_dividends` per neuron and `moving_price` / `tempo` on the
subnet, so "metagraph returns this data" is directly verifiable.

### 5. Tests

- `tests/unit/v1/services/test_apy.py`: deterministic checks of `epochs_per_year`
  and `single_epoch_apy` (incl. `alpha_staked == 0 -> 0.0`, a hand-computed value).
- Extend `tests/unit/v1/services/test_metagraph_extractor.py`: a fake metagraph with
  `alpha_dividends_per_hotkey`, `tao_dividends_per_hotkey`, `pool.moving_price`, `tempo`
  → assert correct hotkey→uid mapping and subnet fields; and a metagraph **missing**
  those attributes → assert defaults (0.0 / 0) and no exception.

## Acceptance criteria

1. `sentinel subnet -u <n> apy` renders a table with non-zero `Alpha Earned` and a
   computed `APY%` for validators on a live (finney) subnet.
2. `sentinel subnet -u <n> -b <historical_block> -n <archive> apy` works for a
   historical block on an archive node.
3. `sentinel subnet -u <n> metagraph --output json` includes `alpha_dividends`,
   `tao_dividends` (per neuron) and `moving_price`, `tempo` (subnet).
4. Unit tests pass; `nox` lint/type-check clean.

## Risks / notes

- Per-hotkey dividend lists are keyed by hotkey string; mapping relies on the neuron's
  axon hotkey matching. Neurons with no dividends entry correctly get 0.0.
- Very old historical blocks may not expose MetagraphInfo dividends; defaults keep the
  extractor from failing (verified by the missing-attr test).
- `single_epoch_apy` annualizes a single epoch and will be volatile epoch-to-epoch;
  it is a verification/shortcut figure, not the reported windowed APY.
