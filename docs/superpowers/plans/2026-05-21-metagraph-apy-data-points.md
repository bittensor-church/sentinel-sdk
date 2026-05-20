# Metagraph APY Data Points Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface the dTAO-era validator-APY data points (per-hotkey net dividends, moving price, tempo) on the sentinel metagraph DTO, and add a `sentinel subnet apy` CLI command that renders single-epoch annualized APY for verification.

**Architecture:** The bittensor `Metagraph` already carries `alpha_dividends_per_hotkey`, `tao_dividends_per_hotkey`, `pool.moving_price`, and `tempo` (via the MetagraphInfo mixin, applied in both lite and non-lite syncs). We read those defensively in `MetagraphExtractor`, add four defaulted fields to the DTO, provide a pure opt-in APY shortcut helper (no calc baked into the DTO), and a CLI command that consumes both.

**Tech Stack:** Python 3.12, pydantic v2 DTOs, typer + rich CLI, pytest. Repo: `/home/aleksandr/bittensor-church/sentinel-sdk`.

---

## Working directory

All paths below are relative to `/home/aleksandr/bittensor-church/sentinel-sdk`. Run all commands from that directory.

## File Structure

- **Create** `src/sentinel/v1/services/apy.py` — pure APY helpers (`epochs_per_year`, `single_epoch_apy`) and `compute_validator_apy_rows` + `ApyRow`. No chain access.
- **Create** `tests/unit/v1/services/test_apy.py` — unit tests for the helpers.
- **Modify** `src/sentinel/v1/services/extractors/metagraph/dto.py` — add `alpha_dividends`/`tao_dividends` to `NeuronSnapshotBase`; `moving_price`/`tempo` to `SubnetBase`.
- **Modify** `src/sentinel/v1/services/extractors/metagraph/extractor.py` — read the new fields from the metagraph.
- **Modify** `tests/unit/v1/services/test_metagraph_extractor.py` — extend with dividends-mapping and subnet moving_price/tempo tests.
- **Modify** `src/sentinel_cli/commands/subnet.py` — add the `apy` command; add the new fields to the existing `metagraph --output json` output.

---

## Task 1: APY shortcut helpers

**Files:**
- Create: `src/sentinel/v1/services/apy.py`
- Test: `tests/unit/v1/services/test_apy.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/v1/services/test_apy.py`:

```python
"""Unit tests for the pure APY shortcut helpers."""

import pytest

from sentinel.v1.services.apy import epochs_per_year, single_epoch_apy

TEMPO = 360
# (tempo + 1) * 12 seconds per epoch
EPOCH_SECONDS = (TEMPO + 1) * 12
EXPECTED_EPOCHS_PER_YEAR = 31_557_600 / EPOCH_SECONDS


def test_epochs_per_year_for_tempo_360():
    assert epochs_per_year(TEMPO) == pytest.approx(EXPECTED_EPOCHS_PER_YEAR)


def test_single_epoch_apy_zero_stake_returns_zero():
    assert single_epoch_apy(alpha_earned=1.0, alpha_staked=0.0, tempo=TEMPO) == 0.0


def test_single_epoch_apy_negative_stake_returns_zero():
    assert single_epoch_apy(alpha_earned=1.0, alpha_staked=-5.0, tempo=TEMPO) == 0.0


def test_single_epoch_apy_compounds_one_epoch_return():
    # r_epoch = 0.01 / 10.0 = 0.001
    expected = ((1 + 0.001) ** EXPECTED_EPOCHS_PER_YEAR - 1) * 100
    result = single_epoch_apy(alpha_earned=0.01, alpha_staked=10.0, tempo=TEMPO)
    assert result == pytest.approx(expected)


def test_single_epoch_apy_zero_earnings_is_zero_percent():
    assert single_epoch_apy(alpha_earned=0.0, alpha_staked=10.0, tempo=TEMPO) == pytest.approx(0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/v1/services/test_apy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sentinel.v1.services.apy'`

- [ ] **Step 3: Write minimal implementation**

Create `src/sentinel/v1/services/apy.py`:

```python
"""Pure APY helpers for dTAO-era validator/staker returns.

These functions take already-extracted data points and apply a *shortcut*
single-epoch annualization. They never touch the chain. The metagraph DTO
deliberately stores raw data points only; clients opt into this calculation
(the formula may be adjusted independently of the SDK).

`alpha_earned` is expected to come from `AlphaDividendsPerSubnet` (metagraph
index 71) and is already net of subnet-owner cut and validator take, so no
correction factors are applied here.
"""

from __future__ import annotations

from dataclasses import dataclass

SECONDS_PER_YEAR = 31_557_600  # 365.25 days
BLOCK_TIME_SECONDS = 12


def epochs_per_year(tempo: int) -> float:
    """Number of epochs in a year for a subnet with the given tempo.

    An epoch spans `tempo + 1` blocks at 12s/block.
    """
    epoch_seconds = (tempo + 1) * BLOCK_TIME_SECONDS
    return SECONDS_PER_YEAR / epoch_seconds


def single_epoch_apy(alpha_earned: float, alpha_staked: float, tempo: int) -> float:
    """Annualize a single epoch's return by compounding (shortcut).

    Returns a percentage. This is NOT a substitute for true windowed APY,
    which samples many epochs; it extrapolates one epoch to a full year and
    is therefore volatile epoch-to-epoch. Guards `alpha_staked <= 0 -> 0.0`.
    """
    if alpha_staked <= 0:
        return 0.0
    r_epoch = alpha_earned / alpha_staked
    return ((1 + r_epoch) ** epochs_per_year(tempo) - 1) * 100
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/v1/services/test_apy.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/sentinel/v1/services/apy.py tests/unit/v1/services/test_apy.py
git commit -m "feat: add pure single-epoch APY shortcut helpers"
```

---

## Task 2: DTO + extractor — per-neuron dividends

**Files:**
- Modify: `src/sentinel/v1/services/extractors/metagraph/dto.py` (`NeuronSnapshotBase`, after the `normalized_stake` field ~line 308)
- Modify: `src/sentinel/v1/services/extractors/metagraph/extractor.py` (`_build_neuron_snapshots`, `_build_single_neuron_snapshot`, new `_build_dividends_maps`)
- Test: `tests/unit/v1/services/test_metagraph_extractor.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/v1/services/test_metagraph_extractor.py`:

```python
class TestDividendDataPoints:
    """alpha/tao dividends (metagraph index 71) are mapped from per-hotkey
    lists onto each neuron by hotkey."""

    @staticmethod
    def _metagraph_with_dividends() -> SimpleNamespace:
        mg = _fake_metagraph(alpha_stake=[10.0, 20.0])
        # `_build_neuron_snapshots` parses `metagraph.n` via `.item()`; the bare
        # int from _fake_metagraph is not subscriptable, so give it an .item().
        mg.n = SimpleNamespace(item=lambda: 2)
        # Distinct hotkeys per uid for an unambiguous mapping (default fake reuses one).
        mg.axons = [_fake_axon(hotkey="5AAA"), _fake_axon(hotkey="5BBB")]
        mg.alpha_dividends_per_hotkey = [("5AAA", 1.5), ("5BBB", 2.5)]
        mg.tao_dividends_per_hotkey = [("5AAA", 0.15), ("5BBB", 0.25)]
        return mg

    def test_build_dividends_maps_from_metagraph(self):
        mg = self._metagraph_with_dividends()
        alpha_map, tao_map = MetagraphExtractor._build_dividends_maps(mg)
        assert alpha_map == {"5AAA": 1.5, "5BBB": 2.5}
        assert tao_map == {"5AAA": 0.15, "5BBB": 0.25}

    def test_build_dividends_maps_empty_when_absent(self):
        mg = _fake_metagraph(alpha_stake=[10.0, 20.0])  # no *_dividends_per_hotkey attrs
        alpha_map, tao_map = MetagraphExtractor._build_dividends_maps(mg)
        assert alpha_map == {}
        assert tao_map == {}

    def test_dividends_mapped_by_hotkey_end_to_end(self):
        mg = self._metagraph_with_dividends()
        block = Block(block_number=1234, timestamp=datetime.now(tz=UTC))
        neurons = _make_extractor()._build_neuron_snapshots([mg], block)

        assert neurons[0].alpha_dividends == 1.5
        assert neurons[0].tao_dividends == 0.15
        assert neurons[1].alpha_dividends == 2.5
        assert neurons[1].tao_dividends == 0.25

    def test_dividends_default_zero_when_metagraph_omits_them(self):
        mg = _fake_metagraph(alpha_stake=[10.0, 20.0])  # no *_dividends_per_hotkey attrs
        mg.n = SimpleNamespace(item=lambda: 2)
        block = Block(block_number=1234, timestamp=datetime.now(tz=UTC))
        neurons = _make_extractor()._build_neuron_snapshots([mg], block)

        assert neurons[0].alpha_dividends == 0.0
        assert neurons[0].tao_dividends == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/v1/services/test_metagraph_extractor.py::TestDividendDataPoints -v`
Expected: FAIL — `pydantic_core.ValidationError` / `AttributeError` because `alpha_dividends` is not a field yet.

- [ ] **Step 3a: Add DTO fields**

In `src/sentinel/v1/services/extractors/metagraph/dto.py`, in `NeuronSnapshotBase`, immediately after the `normalized_stake` field block (the `Annotated[float, Field(ge=0, le=1, ...)]` for `normalized_stake`), add:

```python
    # Dividend metrics (dTAO-era APY inputs; 0.0 if the metagraph does not expose them)
    alpha_dividends: Annotated[
        float,
        Field(
            default=0.0,
            ge=0,
            description=(
                "Net alpha dividends for this neuron's hotkey this epoch (TAO float, "
                "AlphaDividendsPerSubnet index 71). Already net of owner cut and validator take."
            ),
        ),
    ]
    tao_dividends: Annotated[
        float,
        Field(
            default=0.0,
            ge=0,
            description="Net TAO dividends for this neuron's hotkey this epoch (TAO float).",
        ),
    ]
```

- [ ] **Step 3b: Add the dividends-map builder to the extractor**

In `src/sentinel/v1/services/extractors/metagraph/extractor.py`, add this static method (place it next to `_read_alpha_out_emission` near the bottom of the class):

```python
    @staticmethod
    def _build_dividends_maps(
        metagraph: Metagraph,
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Build {hotkey: amount} maps for alpha/tao dividends (index 71).

        Returns empty dicts when the metagraph does not expose the lists
        (e.g. older historical blocks).
        """
        alpha_pairs = getattr(metagraph, "alpha_dividends_per_hotkey", None) or []
        tao_pairs = getattr(metagraph, "tao_dividends_per_hotkey", None) or []
        alpha_map = {hotkey: float(amount) for hotkey, amount in alpha_pairs}
        tao_map = {hotkey: float(amount) for hotkey, amount in tao_pairs}
        return alpha_map, tao_map
```

- [ ] **Step 3c: Build the maps once and thread them through**

In `_build_neuron_snapshots`, after `base_metagraph = metagraphs[0]` and before the `for uid in range(n_neurons):` loop, add:

```python
        alpha_div_map, tao_div_map = self._build_dividends_maps(base_metagraph)
```

Then update the `_build_single_neuron_snapshot(...)` call inside that loop to pass the maps:

```python
            neuron_snapshot = self._build_single_neuron_snapshot(
                metagraph=base_metagraph,
                uid=uid,
                total_subnet_stake=total_subnet_stake,
                mechanisms=mechanisms,
                block=block,
                alpha_div_map=alpha_div_map,
                tao_div_map=tao_div_map,
            )
```

- [ ] **Step 3d: Consume the maps in `_build_single_neuron_snapshot`**

Add the two optional parameters to the signature of `_build_single_neuron_snapshot` (after `block: Block,`):

```python
        alpha_div_map: dict[str, float] | None = None,
        tao_div_map: dict[str, float] | None = None,
```

Inside the method, after `hotkey = axon.hotkey if axon else ""` is computed, add:

```python
        alpha_div_map = alpha_div_map or {}
        tao_div_map = tao_div_map or {}
        alpha_dividends = alpha_div_map.get(hotkey, 0.0)
        tao_dividends = tao_div_map.get(hotkey, 0.0)
```

Then in the `return NeuronSnapshotFull(...)` constructor, add these two keyword arguments (e.g. right after `normalized_stake=float(normalized_stake),`):

```python
            alpha_dividends=alpha_dividends,
            tao_dividends=tao_dividends,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/v1/services/test_metagraph_extractor.py -v`
Expected: PASS — new `TestDividendDataPoints` tests pass and all pre-existing tests still pass (the new params are optional so direct `_build_single_neuron_snapshot` callers are unaffected).

- [ ] **Step 5: Commit**

```bash
git add src/sentinel/v1/services/extractors/metagraph/dto.py \
        src/sentinel/v1/services/extractors/metagraph/extractor.py \
        tests/unit/v1/services/test_metagraph_extractor.py
git commit -m "feat: extract per-neuron alpha/tao dividends (index 71) into metagraph DTO"
```

---

## Task 3: DTO + extractor — subnet moving_price & tempo

**Files:**
- Modify: `src/sentinel/v1/services/extractors/metagraph/dto.py` (`SubnetBase`, after the `alpha_out_emission` field ~line 177)
- Modify: `src/sentinel/v1/services/extractors/metagraph/extractor.py` (`_build_subnet`, the embedded `subnet_dto` in `_build_single_neuron_snapshot`, new `_read_moving_price`/`_read_tempo`)
- Test: `tests/unit/v1/services/test_metagraph_extractor.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/v1/services/test_metagraph_extractor.py`:

```python
class TestSubnetApyFields:
    """moving_price and tempo are read onto the subnet DTO."""

    def test_moving_price_and_tempo_extracted(self):
        mg = _fake_metagraph(alpha_stake=[10.0, 20.0])
        mg.pool = SimpleNamespace(moving_price=0.0345)
        mg.tempo = 360

        subnet = _make_extractor()._build_subnet(mg)

        assert subnet.moving_price == pytest.approx(0.0345)
        assert subnet.tempo == 360

    def test_tempo_falls_back_to_hparams(self):
        mg = _fake_metagraph(alpha_stake=[10.0, 20.0])
        mg.pool = SimpleNamespace(moving_price=0.01)
        mg.tempo = None
        mg.hparams = SimpleNamespace(tempo=99)

        subnet = _make_extractor()._build_subnet(mg)

        assert subnet.tempo == 99

    def test_moving_price_and_tempo_default_zero_when_absent(self):
        mg = _fake_metagraph(alpha_stake=[10.0, 20.0])  # no pool/tempo attrs (hparams is None)

        subnet = _make_extractor()._build_subnet(mg)

        assert subnet.moving_price == 0.0
        assert subnet.tempo == 0
```

Add `import pytest` to the top of the test file if it is not already imported.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/v1/services/test_metagraph_extractor.py::TestSubnetApyFields -v`
Expected: FAIL — `AttributeError`/`ValidationError`: `moving_price`/`tempo` are not fields yet.

- [ ] **Step 3a: Add DTO fields**

In `src/sentinel/v1/services/extractors/metagraph/dto.py`, in `SubnetBase`, immediately after the `alpha_out_emission` field block, add:

```python
    moving_price: Annotated[
        float,
        Field(
            default=0.0,
            ge=0,
            description="Alpha->TAO moving price. 0.0 if the underlying metagraph does not expose it.",
        ),
    ]
    tempo: Annotated[
        int,
        Field(
            default=0,
            ge=0,
            description="Epoch length in blocks. 0 if the underlying metagraph does not expose it.",
        ),
    ]
```

- [ ] **Step 3b: Add reader helpers to the extractor**

In `src/sentinel/v1/services/extractors/metagraph/extractor.py`, add these static methods next to `_read_alpha_out_emission`:

```python
    @staticmethod
    def _read_moving_price(metagraph: Metagraph) -> float:
        """Read the alpha->TAO moving price, 0.0 if not exposed."""
        pool = getattr(metagraph, "pool", None)
        val = getattr(pool, "moving_price", None) if pool is not None else None
        return float(val) if val is not None else 0.0

    @staticmethod
    def _read_tempo(metagraph: Metagraph) -> int:
        """Read subnet tempo (epoch length in blocks), 0 if not exposed."""
        val = getattr(metagraph, "tempo", None)
        if val is None:
            hparams = getattr(metagraph, "hparams", None)
            val = getattr(hparams, "tempo", None) if hparams is not None else None
        return int(val) if val is not None else 0
```

- [ ] **Step 3c: Set the fields in `_build_subnet`**

In `_build_subnet`, in the `return SubnetWithOwner(...)` constructor, add after `alpha_out_emission=self._read_alpha_out_emission(metagraph),`:

```python
            moving_price=self._read_moving_price(metagraph),
            tempo=self._read_tempo(metagraph),
```

- [ ] **Step 3d: Set the fields on the embedded `subnet_dto`**

In `_build_single_neuron_snapshot`, in the `subnet_dto = Subnet(...)` constructor, add after `alpha_out_emission=self._read_alpha_out_emission(metagraph),`:

```python
            moving_price=self._read_moving_price(metagraph),
            tempo=self._read_tempo(metagraph),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/v1/services/test_metagraph_extractor.py -v`
Expected: PASS (all tests, including the existing ones).

- [ ] **Step 5: Commit**

```bash
git add src/sentinel/v1/services/extractors/metagraph/dto.py \
        src/sentinel/v1/services/extractors/metagraph/extractor.py \
        tests/unit/v1/services/test_metagraph_extractor.py
git commit -m "feat: extract subnet moving_price and tempo into metagraph DTO"
```

---

## Task 4: APY row computation helper

**Files:**
- Modify: `src/sentinel/v1/services/apy.py` (add `ApyRow` + `compute_validator_apy_rows`)
- Test: `tests/unit/v1/services/test_apy.py`

- [ ] **Step 1: Write the failing test**

First, update the imports at the **top** of `tests/unit/v1/services/test_apy.py` so the whole module shares them (avoids ruff E402 for mid-file imports):

```python
from types import SimpleNamespace

import pytest

from sentinel.v1.services.apy import compute_validator_apy_rows, epochs_per_year, single_epoch_apy
```

Then append the following tests to the end of `tests/unit/v1/services/test_apy.py`:

```python
def _fake_neuron(uid, hotkey, *, is_validator, alpha_stake, alpha_dividends, tao_dividends=0.0):
    return SimpleNamespace(
        uid=uid,
        is_validator=is_validator,
        alpha_stake=alpha_stake,
        alpha_dividends=alpha_dividends,
        tao_dividends=tao_dividends,
        neuron=SimpleNamespace(hotkey=SimpleNamespace(hotkey=hotkey)),
    )


def test_compute_rows_only_includes_validators():
    neurons = [
        _fake_neuron(0, "5AAA", is_validator=True, alpha_stake=10.0, alpha_dividends=0.01),
        _fake_neuron(1, "5BBB", is_validator=False, alpha_stake=5.0, alpha_dividends=0.02),
    ]
    rows = compute_validator_apy_rows(neurons, tempo=360)
    assert [r.uid for r in rows] == [0]


def test_compute_rows_sorted_by_apy_desc_with_expected_values():
    neurons = [
        _fake_neuron(0, "5AAA", is_validator=True, alpha_stake=100.0, alpha_dividends=0.01),
        _fake_neuron(1, "5BBB", is_validator=True, alpha_stake=10.0, alpha_dividends=0.01),
    ]
    rows = compute_validator_apy_rows(neurons, tempo=360)

    # uid 1 has a higher per-epoch return (0.001 vs 0.0001) -> higher APY -> sorts first.
    assert [r.uid for r in rows] == [1, 0]
    assert rows[0].apy == pytest.approx(single_epoch_apy(0.01, 10.0, 360))
    assert rows[1].apy == pytest.approx(single_epoch_apy(0.01, 100.0, 360))
    assert rows[0].alpha_staked == 10.0
    assert rows[0].alpha_earned == 0.01
    assert rows[0].hotkey == "5BBB"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/v1/services/test_apy.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_validator_apy_rows'`

- [ ] **Step 3: Implement**

Append to `src/sentinel/v1/services/apy.py`:

```python
@dataclass
class ApyRow:
    """A single validator's APY data points for rendering."""

    uid: int
    hotkey: str
    alpha_staked: float
    alpha_earned: float
    tao_earned: float
    apy: float


def compute_validator_apy_rows(neurons: list, tempo: int) -> list["ApyRow"]:
    """Build single-epoch-annualized APY rows for validator neurons.

    `neurons` is any iterable of objects exposing `uid`, `is_validator`,
    `alpha_stake`, `alpha_dividends`, `tao_dividends`, and
    `neuron.hotkey.hotkey` (e.g. NeuronSnapshotFull). Rows are sorted by APY
    descending.
    """
    rows: list[ApyRow] = []
    for neuron in neurons:
        if not getattr(neuron, "is_validator", False):
            continue
        related = getattr(neuron, "neuron", None)
        hotkey_obj = getattr(related, "hotkey", None) if related is not None else None
        hotkey = getattr(hotkey_obj, "hotkey", "") if hotkey_obj is not None else ""
        rows.append(
            ApyRow(
                uid=neuron.uid,
                hotkey=hotkey,
                alpha_staked=neuron.alpha_stake,
                alpha_earned=neuron.alpha_dividends,
                tao_earned=neuron.tao_dividends,
                apy=single_epoch_apy(neuron.alpha_dividends, neuron.alpha_stake, tempo),
            ),
        )
    rows.sort(key=lambda r: r.apy, reverse=True)
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/v1/services/test_apy.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add src/sentinel/v1/services/apy.py tests/unit/v1/services/test_apy.py
git commit -m "feat: add compute_validator_apy_rows helper"
```

---

## Task 5: CLI `apy` command + metagraph JSON fields

**Files:**
- Modify: `src/sentinel_cli/commands/subnet.py` (imports; new `_build_apy_table` + `apy` command; extend `metagraph` JSON branch)

- [ ] **Step 1: Add imports**

In `src/sentinel_cli/commands/subnet.py`, update the existing apy/dividends import line:

```python
from sentinel.v1.services.apy import ApyRow, compute_validator_apy_rows, epochs_per_year
```

(Add it near the existing `from sentinel.v1.services.extractors.dividends import ...` import.)

- [ ] **Step 2: Add the table builder and command**

Append to `src/sentinel_cli/commands/subnet.py`:

```python
def _build_apy_table(rows: list[ApyRow]) -> Table:
    """Build a table of single-epoch-annualized validator APY."""
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("UID", style="cyan", justify="right")
    table.add_column("Hotkey")
    table.add_column("Alpha Staked", justify="right")
    table.add_column("Alpha Earned", justify="right")
    table.add_column("r_epoch", justify="right")
    table.add_column("APY %", justify="right")

    for row in rows:
        hotkey_display = (
            row.hotkey[:HOTKEY_DISPLAY_LENGTH] + "..."
            if len(row.hotkey) > HOTKEY_DISPLAY_LENGTH
            else row.hotkey
        )
        r_epoch = (row.alpha_earned / row.alpha_staked) if row.alpha_staked > 0 else 0.0
        table.add_row(
            str(row.uid),
            hotkey_display,
            f"{row.alpha_staked:.4f}",
            f"{row.alpha_earned:.6f}",
            f"{r_epoch:.6f}",
            f"{row.apy:.2f}",
        )

    return table


@subnet.command()
def apy(
    ctx: typer.Context,
) -> None:
    """Render single-epoch annualized validator APY data points for a subnet."""
    start_time = time.perf_counter()

    netuid = ctx.obj["netuid"]
    block_number = ctx.obj["block_number"]
    mechid = ctx.obj["mechid"]
    lite = ctx.obj["lite"]
    provider: BlockchainProvider = ctx.obj["provider"]

    try:
        resolved_block = resolve_block_number(provider, block_number)
    except BasePylonException as e:
        _handle_pylon_error(e)

    try:
        subnet_instance = Subnet(provider, netuid, resolved_block, mechid, lite=lite)
        snapshot = subnet_instance.metagraph
    except BasePylonException as e:
        _handle_pylon_error(e)
    except StateDiscardedError:
        console.print(
            f"[red]Error:[/red] Block [cyan]{resolved_block}[/cyan] is too old and its state has been discarded.",
        )
        console.print()
        console.print("To query historical blocks, use an archive node:")
        console.print(f"  [dim]--network {ARCHIVE_NODE_URI}[/dim]")
        raise typer.Exit(1) from None

    if not snapshot:
        console.print("[red]Error:[/red] Could not retrieve metagraph data.")
        raise typer.Exit(1)

    tempo = snapshot.subnet.tempo
    moving_price = snapshot.subnet.moving_price
    epochs = epochs_per_year(tempo) if tempo else 0.0
    rows = compute_validator_apy_rows(snapshot.neurons, tempo)

    if is_json_output():
        output_json(
            {
                "block_number": resolved_block,
                "netuid": netuid,
                "tempo": tempo,
                "moving_price": moving_price,
                "epochs_per_year": epochs,
                "validators": [
                    {
                        "uid": row.uid,
                        "hotkey": row.hotkey,
                        "alpha_staked": row.alpha_staked,
                        "alpha_earned": row.alpha_earned,
                        "tao_earned": row.tao_earned,
                        "apy": row.apy,
                    }
                    for row in rows
                ],
            },
        )
    else:
        console.print(f"Block: [cyan]{resolved_block}[/cyan]")
        console.print(f"Subnet: [cyan]{netuid}[/cyan] - {snapshot.subnet.name}")
        console.print(
            f"Tempo: [cyan]{tempo}[/cyan]  "
            f"Moving price: [cyan]{moving_price:.6f}[/cyan] TAO/alpha  "
            f"Epochs/year: [cyan]{epochs:.1f}[/cyan]",
        )
        console.print()
        if not rows:
            console.print("[yellow]No validator dividend data at this block.[/yellow]")
        else:
            console.print(_build_apy_table(rows))
        console.print()
        console.print("[dim]APY is single-epoch annualized (shortcut), alpha-denominated.[/dim]")

    _print_elapsed_time(start_time)
```

- [ ] **Step 3: Add the new fields to the existing `metagraph --output json` output**

In the `metagraph` command's JSON branch (the `elif is_json_output():` block), add to the top-level dict (next to `"alpha_out_emission": snapshot.subnet.alpha_out_emission,`):

```python
                "moving_price": snapshot.subnet.moving_price,
                "tempo": snapshot.subnet.tempo,
```

And in the per-neuron dict inside `"neurons": [...]` (next to `"alpha_stake": neuron.alpha_stake,`), add:

```python
                        "alpha_dividends": neuron.alpha_dividends,
                        "tao_dividends": neuron.tao_dividends,
```

- [ ] **Step 4: Verify the CLI imports and registers without error**

Run: `uv run sentinel subnet --help`
Expected: the subcommand list now includes `apy`. No import errors.

- [ ] **Step 5: Run the full unit suite**

Run: `uv run pytest tests/unit/v1/services/ -v`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
git add src/sentinel_cli/commands/subnet.py
git commit -m "feat: add 'subnet apy' CLI command and expose APY fields in metagraph json"
```

---

## Task 6: Lint, type-check, and live acceptance verification

**Files:** none (verification only)

- [ ] **Step 1: Lint and type-check**

Run: `nox -s lint`
Expected: ruff, ruff format, mypy, codespell all pass clean. Fix any reported issues in the files touched above, then re-run until clean.

- [ ] **Step 2: Full test session**

Run: `nox -s test`
Expected: entire suite passes.

- [ ] **Step 3: Live acceptance — current block (finney)**

Run: `uv run sentinel subnet -u 1 apy`
Expected: a table of validators with non-zero `Alpha Earned` and a computed `APY %`, plus a header line showing a non-zero `Tempo` and `Moving price`. (If subnet 1 is quiet, try an active subnet, e.g. `-u 64`.)

- [ ] **Step 4: Live acceptance — JSON data points round-trip**

The JSON format is the global `-f json` option and must come **before** the `subnet` subcommand group.

Run: `uv run sentinel -f json subnet -u 1 metagraph`
Expected: each neuron object includes `alpha_dividends` and `tao_dividends`; the top level includes `moving_price` and `tempo`.

Also confirm the `apy` command's JSON form: `uv run sentinel -f json subnet -u 1 apy`
Expected: a `validators` array of objects with `uid`, `hotkey`, `alpha_staked`, `alpha_earned`, `tao_earned`, `apy`, plus top-level `tempo`, `moving_price`, `epochs_per_year`.

- [ ] **Step 5: Live acceptance — historical block on archive (optional but recommended)**

Run: `uv run sentinel subnet -u 1 -b <recent_historical_block> -n wss://archive.chain.opentensor.ai:443 apy`
Expected: command succeeds and renders data for the historical block (state-retention permitting). If the block is too old, the command prints the StateDiscarded archive-node hint instead of crashing.

- [ ] **Step 6: Final confirmation**

No commit needed (verification only). Report results: paste the APY table output and confirm lint/tests are green.

---

## Notes for the implementer

- The new `_build_single_neuron_snapshot` parameters are **optional** specifically so the existing direct-call tests in `test_metagraph_extractor.py` keep working unchanged. Do not make them required.
- `alpha_dividends_per_hotkey` is keyed by hotkey string; a neuron with no entry correctly gets `0.0`. This is expected for miners and for historical blocks predating the MetagraphInfo dividends fields.
- Do **not** add `owner_cut` or `hotkey_take` — they are out of scope (already applied inside `alpha_dividends`, per the spec).
- The APY value is the single-epoch shortcut and will look volatile; that is expected and documented in the helper docstring and the CLI footer.
