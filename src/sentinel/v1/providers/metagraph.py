"""
Provider-neutral metagraph model.

The bittensor SDK has reshaped its own metagraph type across majors — v10
exposed parallel tensor columns (``stake``, ``ranks``, ``weights`` as a dense
matrix), v11 exposes a dataclass holding a list of neurons. Providers translate
whatever their backend returns into the types below, so the extractors depend on
sentinel's model rather than on the SDK's current shape.

Weight and bond matrices are sparse here: ``{source_uid: {target_uid: value}}``,
omitting zeros, which is how the chain stores them and how v11 reports them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NeuronRecord:
    """
    One neuron's row of a subnet's metagraph.

    Scores are normalized to 0..1. Stakes and ``emission`` are in the subnet's
    own units (``tao_stake`` is root TAO), as floats rather than SDK balance
    objects so the DTO layer needs no further unwrapping.
    """

    uid: int
    hotkey: str = ""
    coldkey: str = ""
    axon_address: str = ""
    active: bool = False
    validator_permit: bool = False
    last_update: int = 0
    block_at_registration: int = 0
    rank: float = 0.0
    trust: float = 0.0
    consensus: float = 0.0
    incentive: float = 0.0
    dividends: float = 0.0
    validator_trust: float = 0.0
    pruning_score: float = 0.0
    emission: float = 0.0
    total_stake: float = 0.0
    alpha_stake: float = 0.0
    tao_stake: float = 0.0
    identity_name: str | None = None


@dataclass
class SubnetMetagraph:
    """
    A subnet's neurons plus its subnet-level state at one block.

    ``neurons`` is ordered by uid. ``weights`` and ``bonds`` are None on a lite
    read, which is the difference between "not fetched" and an empty matrix.
    """

    netuid: int
    mechid: int = 0
    name: str = ""
    block: int = 0
    tempo: int = 0
    immunity_period: int = 0
    owner_hotkey: str = ""
    owner_coldkey: str = ""
    moving_price: float = 0.0
    alpha_out_emission: float = 0.0
    lite: bool = True
    neurons: list[NeuronRecord] = field(default_factory=list)
    weights: dict[int, dict[int, float]] | None = None
    bonds: dict[int, dict[int, float]] | None = None
    alpha_dividends_per_hotkey: dict[str, float] = field(default_factory=dict)
    tao_dividends_per_hotkey: dict[str, float] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.neurons)

    @property
    def hotkeys(self) -> list[str]:
        return [n.hotkey for n in self.neurons]

    @property
    def coldkeys(self) -> list[str]:
        return [n.coldkey for n in self.neurons]

    def neuron(self, uid: int) -> NeuronRecord | None:
        """The neuron at a uid, or None when the uid is not in the graph."""
        if 0 <= uid < len(self.neurons):
            return self.neurons[uid]
        return None

    def total_stake_sum(self) -> float:
        """Summed stake across the subnet, used to normalize per-neuron stake."""
        return sum(n.total_stake for n in self.neurons)

    def weights_sum(self, uid: int) -> float:
        """Total weight ``uid`` sets on others, 0.0 when it sets none."""
        if not self.weights:
            return 0.0
        return sum(self.weights.get(uid, {}).values())

    def has_incoming_weights(self, uid: int) -> bool:
        """Whether any validator sets a non-zero weight on ``uid``."""
        if not self.weights:
            return False
        return any(row.get(uid, 0.0) > 0 for row in self.weights.values())
