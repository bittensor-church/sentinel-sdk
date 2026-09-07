"""Tests for the DividendsExtractor."""

import numpy as np
import pytest

from sentinel.v1.providers.metagraph import NeuronRecord, SubnetMetagraph
from sentinel.v1.services.extractors.dividends import (
    DividendRecord,
    DividendsExtractor,
    DividendsResult,
)
from sentinel.v1.testing.providers import FakeBlockchainProvider

BLOCK = 100
NETUID = 1


def _metagraph(**overrides) -> SubnetMetagraph:
    """Two validators (uids 0, 1) holding stake and two miners (uids 2, 3) earning incentive."""
    defaults = {
        "netuid": NETUID,
        "block": BLOCK,
        "lite": False,
        "bonds": {},
        "neurons": [
            NeuronRecord(
                uid=0,
                hotkey="hotkey_0",
                identity_name="Validator A",
                active=True,
                validator_permit=True,
                total_stake=100.0,
            ),
            NeuronRecord(
                uid=1,
                hotkey="hotkey_1",
                identity_name="Validator B",
                active=True,
                validator_permit=True,
                total_stake=200.0,
            ),
            NeuronRecord(uid=2, hotkey="hotkey_2", active=True, incentive=0.5),
            NeuronRecord(uid=3, hotkey="hotkey_3", identity_name="Miner D", active=True, incentive=0.5),
        ],
    }
    return SubnetMetagraph(**{**defaults, **overrides})


def _provider(metagraph: SubnetMetagraph | None, yuma_version: int = 3) -> FakeBlockchainProvider:
    provider = FakeBlockchainProvider().with_hyperparams(BLOCK, NETUID, {"yuma_version": yuma_version})
    if metagraph is not None:
        provider.with_metagraph(metagraph, block_number=BLOCK)
    return provider


class TestDividendsExtractor:
    """Tests for DividendsExtractor."""

    def test_extract_returns_dividends_result(self):
        extractor = DividendsExtractor(_provider(_metagraph()), block_number=BLOCK, netuid=NETUID)
        result = extractor.extract()

        assert isinstance(result, DividendsResult)
        assert isinstance(result.records, list)
        assert result.mechid == 0

    def test_extract_missing_metagraph(self):
        """A subnet that does not exist at the block yields no records rather than an error."""
        extractor = DividendsExtractor(_provider(None), block_number=BLOCK, netuid=NETUID)
        result = extractor.extract()

        assert result.records == []
        assert result.yuma3_enabled is True

    def test_extract_empty_metagraph(self):
        """A registered subnet with no neurons yields no records."""
        extractor = DividendsExtractor(
            _provider(_metagraph(neurons=[])),
            block_number=BLOCK,
            netuid=NETUID,
        )

        assert extractor.extract().records == []

    def test_extract_creates_dividend_records(self):
        extractor = DividendsExtractor(_provider(_metagraph()), block_number=BLOCK, netuid=NETUID)
        result = extractor.extract()

        assert len(result.records) == 4
        assert all(isinstance(r, DividendRecord) for r in result.records)
        assert result.records[0].hotkey == "hotkey_0"
        assert result.records[0].identity_name == "Validator A"
        assert result.records[1].identity_name == "Validator B"
        assert result.records[2].identity_name is None
        assert result.records[0].stake == 100.0

    @pytest.mark.parametrize(("yuma_version", "expected"), [(3, True), (2, False)])
    def test_yuma_version_detection(self, yuma_version: int, expected: bool):
        """yuma3_enabled is read from the subnet's hyperparameters."""
        extractor = DividendsExtractor(
            _provider(_metagraph(), yuma_version=yuma_version),
            block_number=BLOCK,
            netuid=NETUID,
        )

        assert extractor.extract().yuma3_enabled is expected

    def test_yuma3_is_assumed_when_hyperparams_are_unavailable(self):
        provider = FakeBlockchainProvider().with_metagraph(_metagraph(), block_number=BLOCK)
        extractor = DividendsExtractor(provider, block_number=BLOCK, netuid=NETUID)

        assert extractor.extract().yuma3_enabled is True

    def test_missing_bonds_are_reported_rather_than_scored_as_zero(self):
        """Without bonds every dividend would come out zero, which reads as a real
        result — fail loudly instead."""
        extractor = DividendsExtractor(
            _provider(_metagraph(bonds=None)),
            block_number=BLOCK,
            netuid=NETUID,
        )

        with pytest.raises(ValueError, match="Bonds unavailable"):
            extractor.extract()

    def test_dividends_follow_bonds_and_incentive(self):
        """Validator 1 bonds more heavily to the miners and holds more stake, so it
        must take the larger share."""
        metagraph = _metagraph(
            bonds={
                0: {2: 100.0, 3: 50.0},
                1: {2: 80.0, 3: 120.0},
            },
        )
        extractor = DividendsExtractor(_provider(metagraph), block_number=BLOCK, netuid=NETUID)

        result = extractor.extract()
        by_uid = {r.uid: r.dividend for r in result.records}

        assert np.isclose(sum(by_uid.values()), 1.0)
        assert by_uid[1] > by_uid[0] > 0
        # Miners hold no validator permit, so they earn no dividends.
        assert by_uid[2] == 0.0
        assert by_uid[3] == 0.0


class TestToDense:
    """Tests for the sparse-to-dense bond conversion."""

    def test_to_dense_empty(self):
        result = DividendsExtractor._to_dense({}, num_uids=4)

        assert result.shape == (4, 4)
        assert np.all(result == 0)

    def test_to_dense_with_bonds(self):
        sparse_bonds = {
            0: {2: 100.0, 3: 50.0},  # Validator 0 bonds to miners 2, 3
            1: {2: 80.0, 3: 120.0},  # Validator 1 bonds to miners 2, 3
        }

        result = DividendsExtractor._to_dense(sparse_bonds, num_uids=4)

        assert result.shape == (4, 4)
        assert result[0, 2] == 100.0
        assert result[0, 3] == 50.0
        assert result[1, 2] == 80.0
        assert result[1, 3] == 120.0
        assert result[2, 0] == 0  # Miners don't bond

    def test_to_dense_ignores_uids_outside_the_matrix(self):
        """A bond referencing a uid beyond the graph must not raise or resize."""
        result = DividendsExtractor._to_dense({0: {9: 1.0}, 9: {0: 1.0}}, num_uids=2)

        assert result.shape == (2, 2)
        assert np.all(result == 0)


class TestCalculateDividends:
    """Tests for _calculate_dividends method."""

    def test_yuma3_calculation(self):
        # 2 validators, 2 miners
        bonds = np.array(
            [
                [0.0, 0.0, 100.0, 50.0],  # Validator 0
                [0.0, 0.0, 80.0, 120.0],  # Validator 1
                [0.0, 0.0, 0.0, 0.0],  # Miner 2
                [0.0, 0.0, 0.0, 0.0],  # Miner 3
            ]
        )
        incentives = np.array([0.0, 0.0, 0.6, 0.4])  # Miners have incentives
        active_stake = np.array([0.4, 0.6, 0.0, 0.0])  # Normalized validator stake

        dividends = DividendsExtractor._calculate_dividends(
            bonds,
            incentives,
            active_stake,
            yuma3_enabled=True,
        )

        # Should sum to 1 (normalized)
        assert np.isclose(dividends.sum(), 1.0)
        # Validators should have dividends, miners should have 0
        assert dividends[2] == 0
        assert dividends[3] == 0

    def test_bond_scale_does_not_change_the_result(self):
        """v11 reports bonds scaled to 0..1 where v10 reported raw u16; both Yuma
        paths renormalize, so a constant factor must cancel out."""
        bonds = np.array(
            [
                [0.0, 0.0, 100.0, 50.0],
                [0.0, 0.0, 80.0, 120.0],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0],
            ]
        )
        incentives = np.array([0.0, 0.0, 0.6, 0.4])
        active_stake = np.array([0.4, 0.6, 0.0, 0.0])

        scaled = DividendsExtractor._calculate_dividends(
            bonds / 65535,
            incentives,
            active_stake,
            yuma3_enabled=True,
        )
        raw = DividendsExtractor._calculate_dividends(
            bonds,
            incentives,
            active_stake,
            yuma3_enabled=True,
        )

        assert np.allclose(scaled, raw)

    def test_yuma2_calculation(self):
        # Yuma2: dividends = B^T @ I
        # B^T[i,j] = B[j,i], so dividends[i] = sum_j(B[j,i] * I[j])
        bonds = np.array(
            [
                [0.5, 0.3, 0.2, 0.0],
                [0.4, 0.4, 0.2, 0.0],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0],
            ]
        )
        incentives = np.array([0.3, 0.3, 0.2, 0.2])
        active_stake = np.array([0.4, 0.6, 0.0, 0.0])

        dividends = DividendsExtractor._calculate_dividends(
            bonds,
            incentives,
            active_stake,
            yuma3_enabled=False,
        )

        # Should sum to 1 (normalized) when there are non-zero dividends
        assert np.isclose(dividends.sum(), 1.0)
        # B^T @ I produces a result vector
        assert dividends.shape == (4,)

    def test_zero_dividends_sum(self):
        """Handling when all dividends are zero — no division by zero."""
        dividends = DividendsExtractor._calculate_dividends(
            np.zeros((4, 4)),
            np.zeros(4),
            np.zeros(4),
            yuma3_enabled=True,
        )

        assert np.all(dividends == 0)
