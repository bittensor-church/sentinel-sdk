"""Tests for the DividendsExtractor."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from sentinel.v1.services.extractors.dividends import (
    DividendRecord,
    DividendsExtractor,
    DividendsResult,
)


@pytest.fixture
def mock_subtensor() -> MagicMock:
    """Create a mock subtensor instance."""
    return MagicMock()


@pytest.fixture
def mock_metagraph() -> MagicMock:
    """Create a mock metagraph with test data."""
    metagraph = MagicMock()
    metagraph.hotkeys = ["hotkey_0", "hotkey_1", "hotkey_2", "hotkey_3"]
    metagraph.identities = [
        {"name": "Validator A"},
        {"name": "Validator B"},
        None,
        {"name": "Miner D"},
    ]
    metagraph.incentive = [0.0, 0.0, 0.5, 0.5]  # Only miners have incentives
    metagraph.total_stake = [100.0, 200.0, 0.0, 0.0]  # Only validators have stake
    metagraph.active = [True, True, True, True]
    metagraph.validator_permit = [True, True, False, False]  # 0, 1 are validators
    return metagraph


@pytest.fixture
def mock_hyperparams() -> MagicMock:
    """Create mock hyperparameters."""
    hyperparams = MagicMock()
    hyperparams.yuma_version = 3  # Yuma3
    return hyperparams


class TestDividendsExtractor:
    """Tests for DividendsExtractor."""

    def test_extract_returns_dividends_result(
        self,
        mock_subtensor: MagicMock,
        mock_metagraph: MagicMock,
        mock_hyperparams: MagicMock,
    ):
        """Test that extract returns a DividendsResult."""
        mock_subtensor.metagraph.return_value = mock_metagraph
        mock_subtensor.get_subnet_hyperparameters.return_value = mock_hyperparams
        mock_subtensor.bonds.return_value = []

        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)
        result = extractor.extract()

        assert isinstance(result, DividendsResult)
        assert isinstance(result.records, list)
        assert result.mechid == 0

    def test_extract_empty_metagraph(self, mock_subtensor: MagicMock):
        """Test that extract handles None metagraph."""
        mock_subtensor.metagraph.return_value = None

        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)
        result = extractor.extract()

        assert result.records == []
        assert result.yuma3_enabled is True

    def test_extract_empty_hotkeys(
        self,
        mock_subtensor: MagicMock,
        mock_hyperparams: MagicMock,
    ):
        """Test that extract handles metagraph with no hotkeys."""
        metagraph = MagicMock()
        metagraph.hotkeys = []
        mock_subtensor.metagraph.return_value = metagraph
        mock_subtensor.get_subnet_hyperparameters.return_value = mock_hyperparams

        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)
        result = extractor.extract()

        assert result.records == []

    def test_extract_creates_dividend_records(
        self,
        mock_subtensor: MagicMock,
        mock_metagraph: MagicMock,
        mock_hyperparams: MagicMock,
    ):
        """Test that extract creates DividendRecord for each UID."""
        mock_subtensor.metagraph.return_value = mock_metagraph
        mock_subtensor.get_subnet_hyperparameters.return_value = mock_hyperparams
        mock_subtensor.bonds.return_value = []

        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)
        result = extractor.extract()

        assert len(result.records) == 4
        assert all(isinstance(r, DividendRecord) for r in result.records)
        assert result.records[0].hotkey == "hotkey_0"
        assert result.records[0].identity_name == "Validator A"
        assert result.records[1].identity_name == "Validator B"
        assert result.records[2].identity_name is None

    def test_yuma_version_detection(
        self,
        mock_subtensor: MagicMock,
        mock_metagraph: MagicMock,
    ):
        """Test that yuma3_enabled is correctly detected from hyperparams."""
        mock_subtensor.metagraph.return_value = mock_metagraph
        mock_subtensor.bonds.return_value = []

        # Test Yuma3 (version = 3)
        hyperparams_v3 = MagicMock()
        hyperparams_v3.yuma_version = 3
        mock_subtensor.get_subnet_hyperparameters.return_value = hyperparams_v3

        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)
        result = extractor.extract()
        assert result.yuma3_enabled is True

        # Test Yuma2 (version = 2)
        hyperparams_v2 = MagicMock()
        hyperparams_v2.yuma_version = 2
        mock_subtensor.get_subnet_hyperparameters.return_value = hyperparams_v2

        result = extractor.extract()
        assert result.yuma3_enabled is False


class TestSpareToDense:
    """Tests for _sparse_to_dense method."""

    def test_sparse_to_dense_empty(self, mock_subtensor: MagicMock):
        """Test sparse to dense with empty bonds."""
        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)
        result = extractor._sparse_to_dense([], num_uids=4)

        assert result.shape == (4, 4)
        assert np.all(result == 0)

    def test_sparse_to_dense_with_bonds(self, mock_subtensor: MagicMock):
        """Test sparse to dense with actual bonds."""
        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)

        # Sparse format: [(uid, [(target_uid, bond_value), ...])]
        sparse_bonds = [
            (0, [(2, 100.0), (3, 50.0)]),  # Validator 0 bonds to miners 2, 3
            (1, [(2, 80.0), (3, 120.0)]),  # Validator 1 bonds to miners 2, 3
        ]

        result = extractor._sparse_to_dense(sparse_bonds, num_uids=4)

        assert result.shape == (4, 4)
        assert result[0, 2] == 100.0
        assert result[0, 3] == 50.0
        assert result[1, 2] == 80.0
        assert result[1, 3] == 120.0
        assert result[2, 0] == 0  # Miners don't bond


class TestCalculateDividends:
    """Tests for _calculate_dividends method."""

    def test_yuma3_calculation(self, mock_subtensor: MagicMock):
        """Test Yuma3 dividend calculation."""
        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)

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

        dividends = extractor._calculate_dividends(
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

    def test_yuma2_calculation(self, mock_subtensor: MagicMock):
        """Test Yuma2 dividend calculation (B^T @ I)."""
        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)

        # Yuma2: dividends = B^T @ I
        # B^T[i,j] = B[j,i], so dividends[i] = sum_j(B[j,i] * I[j])
        # Use a simpler matrix where B^T @ I produces non-zero results
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

        dividends = extractor._calculate_dividends(
            bonds,
            incentives,
            active_stake,
            yuma3_enabled=False,
        )

        # Should sum to 1 (normalized) when there are non-zero dividends
        assert np.isclose(dividends.sum(), 1.0)
        # B^T @ I produces a result vector
        assert dividends.shape == (4,)

    def test_zero_dividends_sum(self, mock_subtensor: MagicMock):
        """Test handling when all dividends are zero."""
        extractor = DividendsExtractor(mock_subtensor, block_number=100, netuid=1)

        bonds = np.zeros((4, 4))
        incentives = np.zeros(4)
        active_stake = np.zeros(4)

        dividends = extractor._calculate_dividends(
            bonds,
            incentives,
            active_stake,
            yuma3_enabled=True,
        )

        # Should handle gracefully without division by zero
        assert np.all(dividends == 0)


class TestGetIdentityName:
    """Tests for _get_identity_name static method."""

    def test_identity_name_from_dict(self):
        """Test extracting name from dict identity."""
        identity = {"name": "Test Validator"}
        result = DividendsExtractor._get_identity_name(identity)
        assert result == "Test Validator"

    def test_identity_name_from_object(self):
        """Test extracting name from object identity."""
        identity = MagicMock()
        identity.name = "Object Validator"
        result = DividendsExtractor._get_identity_name(identity)
        assert result == "Object Validator"

    def test_identity_name_none(self):
        """Test handling None identity."""
        result = DividendsExtractor._get_identity_name(None)
        assert result is None

    def test_identity_no_name_attribute(self):
        """Test handling object without name attribute."""
        identity = MagicMock(spec=[])  # Empty spec, no attributes
        result = DividendsExtractor._get_identity_name(identity)
        assert result is None
