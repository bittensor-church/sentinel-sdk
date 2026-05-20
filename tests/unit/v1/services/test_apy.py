"""Unit tests for the pure APY shortcut helpers."""

from types import SimpleNamespace

import pytest

from sentinel.v1.services.apy import compute_validator_apy_rows, epochs_per_year, single_epoch_apy

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


def test_single_epoch_apy_zero_tempo_returns_zero():
    assert single_epoch_apy(alpha_earned=0.01, alpha_staked=10.0, tempo=0) == 0.0


def test_single_epoch_apy_negative_tempo_returns_zero():
    assert single_epoch_apy(alpha_earned=0.01, alpha_staked=10.0, tempo=-1) == 0.0


def test_single_epoch_apy_compounds_one_epoch_return():
    # r_epoch = 0.01 / 10.0 = 0.001
    expected = ((1 + 0.001) ** EXPECTED_EPOCHS_PER_YEAR - 1) * 100
    result = single_epoch_apy(alpha_earned=0.01, alpha_staked=10.0, tempo=TEMPO)
    assert result == pytest.approx(expected)


def test_single_epoch_apy_zero_earnings_is_zero_percent():
    assert single_epoch_apy(alpha_earned=0.0, alpha_staked=10.0, tempo=TEMPO) == pytest.approx(0.0)


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
    assert rows[0].alpha_dividends == 0.01
    assert rows[0].hotkey == "5BBB"


def test_compute_rows_passes_tao_dividends_through():
    neurons = [
        _fake_neuron(0, "5AAA", is_validator=True, alpha_stake=10.0, alpha_dividends=0.01, tao_dividends=0.5),
    ]
    rows = compute_validator_apy_rows(neurons, tempo=360)
    assert rows[0].tao_dividends == pytest.approx(0.5)


def test_compute_rows_defends_missing_hotkey_path():
    # Neuron without a nested neuron.hotkey path should still produce a row with hotkey="".
    neuron = SimpleNamespace(
        uid=7,
        is_validator=True,
        alpha_stake=10.0,
        alpha_dividends=0.01,
        tao_dividends=0.0,
        neuron=None,
    )
    rows = compute_validator_apy_rows([neuron], tempo=360)
    assert rows[0].hotkey == ""
    assert rows[0].uid == 7
