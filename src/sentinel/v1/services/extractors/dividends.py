from dataclasses import dataclass

import numpy as np

from sentinel.v1.providers.base import BlockchainProvider

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

    def __init__(
        self,
        provider: BlockchainProvider,
        block_number: int,
        netuid: int,
        mechid: int = 0,
    ) -> None:
        self.provider = provider
        self.block_number = block_number
        self.netuid = netuid
        self.mechid = mechid

    def extract(self) -> DividendsResult:
        """Extract dividends for each identity in the subnet."""
        metagraph = self.provider.get_metagraph(
            netuid=self.netuid,
            block_number=self.block_number,
            mechid=self.mechid,
            lite=False,
        )
        if metagraph is None:
            return DividendsResult(records=[], yuma3_enabled=True, mechid=self.mechid)

        # Check which Yuma version is enabled (yuma_version: 1, 2, or 3)
        hyperparams = self.provider.get_subnet_hyperparams(block_number=self.block_number, netuid=self.netuid)
        yuma_version = (hyperparams or {}).get("yuma_version", YUMA_VERSION_3)
        yuma3_enabled = yuma_version == YUMA_VERSION_3

        num_uids = len(metagraph)
        if num_uids == 0:
            return DividendsResult(records=[], yuma3_enabled=yuma3_enabled, mechid=self.mechid)

        if metagraph.bonds is None:
            msg = (
                f"Bonds unavailable for netuid {self.netuid} at block {self.block_number}; "
                f"dividends cannot be derived without them."
            )
            raise ValueError(msg)

        incentives = np.array([n.incentive for n in metagraph.neurons], dtype=np.float64)
        bonds_matrix = self._to_dense(metagraph.bonds, num_uids)

        # Active stake = total_stake masked to only active validators
        total_stake = np.array([n.total_stake for n in metagraph.neurons], dtype=np.float64)
        active_mask = np.array([n.active for n in metagraph.neurons], dtype=bool)
        validator_mask = np.array([n.validator_permit for n in metagraph.neurons], dtype=bool)
        active_stake = total_stake * active_mask * validator_mask

        # Normalize active stake
        stake_sum = active_stake.sum()
        if stake_sum > 0:
            active_stake = active_stake / stake_sum

        dividends = self._calculate_dividends(
            bonds_matrix,
            incentives,
            active_stake,
            yuma3_enabled=yuma3_enabled,
        )

        records = [
            DividendRecord(
                uid=neuron.uid,
                hotkey=neuron.hotkey,
                identity_name=neuron.identity_name,
                dividend=dividends[neuron.uid],
                stake=neuron.total_stake,
            )
            for neuron in metagraph.neurons
        ]

        return DividendsResult(records=records, yuma3_enabled=yuma3_enabled, mechid=self.mechid)

    @staticmethod
    def _to_dense(bonds: dict[int, dict[int, float]], num_uids: int) -> np.ndarray:
        """
        Expand the sparse ``{validator: {miner: bond}}`` map into a dense matrix.

        The absolute bond scale does not matter here: both Yuma paths below
        renormalize, so a constant factor cancels out.
        """
        bonds_matrix = np.zeros((num_uids, num_uids), dtype=np.float64)

        for uid, targets in bonds.items():
            for target_uid, bond_value in targets.items():
                if uid < num_uids and target_uid < num_uids:
                    bonds_matrix[uid, target_uid] = bond_value

        return bonds_matrix

    @staticmethod
    def _calculate_dividends(
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
