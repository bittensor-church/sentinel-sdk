from dataclasses import dataclass

import numpy as np
from bittensor.core.subtensor import Subtensor  # type: ignore[import-untyped]

YUMA_VERSION_3 = 3


@dataclass
class DividendRecord:
    """Dividend record for a single UID."""

    uid: int
    hotkey: str
    identity_name: str | None
    dividend: float
    stake: float


@dataclass
class DividendsResult:
    """Result of dividends extraction."""

    records: list[DividendRecord]
    yuma3_enabled: bool
    mechid: int


class DividendsExtractor:
    """
    Extract dividends for each validator based on Yuma3 consensus.

    Formula (from subtensor):
        1. ema_bonds_norm = col_normalize(ema_bonds)
        2. total_bonds_per_validator[i] = Σ_j ema_bonds_norm[i][j] * incentive[j]
        3. dividends[i] = total_bonds_per_validator[i] * active_stake[i]
        4. normalize(dividends) so Σ_i dividends[i] = 1
    """

    def __init__(self, subtensor: Subtensor, block_number: int, netuid: int, mechid: int = 0) -> None:
        self.subtensor = subtensor
        self.block_number = block_number
        self.netuid = netuid
        self.mechid = mechid

    def extract(self) -> DividendsResult:
        """Extract dividends for each identity in the subnet."""
        metagraph = self.subtensor.metagraph(netuid=self.netuid, block=self.block_number, mechid=self.mechid)
        if metagraph is None:
            return DividendsResult(records=[], yuma3_enabled=True, mechid=self.mechid)

        # Check which Yuma version is enabled (yuma_version: 1, 2, or 3)
        hyperparams = self.subtensor.get_subnet_hyperparameters(netuid=self.netuid, block=self.block_number)

        yuma_version = getattr(hyperparams, "yuma_version", YUMA_VERSION_3) if hyperparams else YUMA_VERSION_3
        yuma3_enabled = yuma_version == YUMA_VERSION_3

        num_uids = len(metagraph.hotkeys)
        if num_uids == 0:
            return DividendsResult(records=[], yuma3_enabled=yuma3_enabled, mechid=self.mechid)

        # Get incentives from metagraph
        incentives = np.array(metagraph.incentive, dtype=np.float64)

        # Get bonds matrix - sparse format: list of (uid, [(target_uid, bond_value), ...])
        bonds_sparse = self.subtensor.bonds(netuid=self.netuid, block=self.block_number)

        # Convert sparse bonds to dense matrix (validator x miner)
        bonds_matrix = self._sparse_to_dense(bonds_sparse, num_uids)

        # Get active stake for each validator (filtered by active status and validator permit)
        total_stake = np.array([float(s) for s in metagraph.total_stake], dtype=np.float64)
        active_mask = np.array(metagraph.active, dtype=bool)
        validator_mask = np.array(metagraph.validator_permit, dtype=bool)

        # Active stake = total_stake masked to only active validators
        active_stake = total_stake * active_mask * validator_mask

        # Normalize active stake
        stake_sum = active_stake.sum()
        if stake_sum > 0:
            active_stake = active_stake / stake_sum

        # Calculate dividends using appropriate Yuma formula
        dividends = self._calculate_dividends(
            bonds_matrix,
            incentives,
            active_stake,
            yuma3_enabled=yuma3_enabled,
        )

        # Build result records
        results = []
        for uid in range(num_uids):
            identity = metagraph.identities[uid] if uid < len(metagraph.identities) else None
            identity_name = self._get_identity_name(identity)

            results.append(
                DividendRecord(
                    uid=uid,
                    hotkey=metagraph.hotkeys[uid],
                    identity_name=identity_name,
                    dividend=dividends[uid],
                    stake=float(total_stake[uid]),
                ),
            )

        return DividendsResult(records=results, yuma3_enabled=yuma3_enabled, mechid=self.mechid)

    def _sparse_to_dense(self, bonds_sparse: list, num_uids: int) -> np.ndarray:
        """Convert sparse bonds to dense matrix."""
        bonds_matrix = np.zeros((num_uids, num_uids), dtype=np.float64)

        for uid, targets in bonds_sparse:
            for target_uid, bond_value in targets:
                if uid < num_uids and target_uid < num_uids:
                    bonds_matrix[uid, target_uid] = bond_value

        return bonds_matrix

    def _calculate_dividends(
        self,
        bonds: np.ndarray,
        incentives: np.ndarray,
        active_stake: np.ndarray,
        *,
        yuma3_enabled: bool = True,
    ) -> np.ndarray:
        """
        Calculate dividends using Yuma consensus formula.

        Args:
            bonds: EMA bonds matrix (validator x miner)
            incentives: Incentive vector for each miner
            active_stake: Active stake for each validator
            yuma3_enabled: If True use Yuma3, else use Yuma2

        Returns:
            Normalized dividend vector

        """
        if yuma3_enabled:
            # Yuma3: col_normalize, multiply by incentives, then by stake
            col_sums = bonds.sum(axis=0)
            col_sums = np.where(col_sums == 0, 1.0, col_sums)
            bonds_normalized = bonds / col_sums

            total_bonds_per_validator = (bonds_normalized * incentives).sum(axis=1)
            dividends = total_bonds_per_validator * active_stake
        else:
            # Yuma2: B^T @ I (transpose bonds, matrix multiply with incentives)
            dividends = bonds.T @ incentives

        # Normalize so sum = 1
        dividends_sum = dividends.sum()
        if dividends_sum > 0:
            dividends = dividends / dividends_sum

        return dividends

    @staticmethod
    def _get_identity_name(identity: dict | object | None) -> str | None:
        """Extract name from identity, handling both dict and object types."""
        if not identity:
            return None
        return identity["name"] if isinstance(identity, dict) else getattr(identity, "name", None)
