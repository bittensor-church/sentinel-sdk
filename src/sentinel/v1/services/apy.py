"""
Pure APY helpers for dTAO-era validator/staker returns.

These functions take already-extracted data points and apply a *shortcut*
single-epoch annualization. They never touch the chain. The metagraph DTO
deliberately stores raw data points only; clients opt into this calculation
(the formula may be adjusted independently of the SDK).

`alpha_earned` is expected to come from `AlphaDividendsPerSubnet` (metagraph
index 71) and is already net of subnet-owner cut and validator take, so no
correction factors are applied here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

SECONDS_PER_YEAR = 31_557_600  # 365.25 days
BLOCK_TIME_SECONDS = 12


def epochs_per_year(tempo: int) -> float:
    """
    Number of epochs in a year for a subnet with the given tempo.

    An epoch spans `tempo + 1` blocks at 12s/block.
    """
    epoch_seconds = (tempo + 1) * BLOCK_TIME_SECONDS
    return SECONDS_PER_YEAR / epoch_seconds


def single_epoch_apy(alpha_earned: float, alpha_staked: float, tempo: int) -> float:
    """
    Annualize a single epoch's return by compounding (shortcut).

    Returns a percentage. This is NOT a substitute for true windowed APY,
    which samples many epochs; it extrapolates one epoch to a full year and
    is therefore volatile epoch-to-epoch.

    Notes on inputs:
    - `alpha_earned` is expected to be the net per-hotkey dividend for this
      epoch (e.g. from `AlphaDividendsPerSubnet`, metagraph index 71), already
      net of subnet-owner cut and validator take.
    - `alpha_staked` is the validator's stake base. Sentinel currently passes
      the metagraph's *current* per-uid `alpha_stake`, not the chain's exact
      base `TotalHotkeyAlphaLastEpoch`. The two can drift within an epoch;
      using current `alpha_stake` is an approximation deferred to follow-up.

    Guards alpha_staked <= 0 or tempo <= 0 -> 0.0.
    """
    if alpha_staked <= 0 or tempo <= 0:
        return 0.0
    r_epoch = alpha_earned / alpha_staked
    return ((1 + r_epoch) ** epochs_per_year(tempo) - 1) * 100


@dataclass
class ApyRow:
    """A single validator's APY data points for rendering."""

    uid: int
    hotkey: str
    alpha_staked: float
    alpha_dividends: float
    tao_dividends: float
    apy: float


def compute_validator_apy_rows(neurons: Sequence[Any], tempo: int) -> list[ApyRow]:
    """
    Build single-epoch-annualized APY rows for validator neurons.

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
                alpha_dividends=neuron.alpha_dividends,
                tao_dividends=neuron.tao_dividends,
                apy=single_epoch_apy(neuron.alpha_dividends, neuron.alpha_stake, tempo),
            ),
        )
    rows.sort(key=lambda r: r.apy, reverse=True)
    return rows
