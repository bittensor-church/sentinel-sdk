from pydantic import BaseModel, ConfigDict


class HyperparametersDTO(BaseModel):
    """Data transfer object for block hyperparameters."""

    model_config = ConfigDict(frozen=True)

    rho: int
    kappa: float
    immunity_period: int
    min_allowed_weights: int
    max_weight_limit: float = 0.0
    tempo: int
    min_difficulty: int
    max_difficulty: int
    weights_version: int
    weights_rate_limit: int
    adjustment_interval: int
    activity_cutoff: int
    registration_allowed: bool
    target_regs_per_interval: int
    min_burn: int
    max_burn: int
    bonds_moving_avg: float
    max_regs_per_block: int
    serving_rate_limit: int
    max_validators: int
    adjustment_alpha: float
    difficulty: int
    commit_reveal_weights_interval: int = 0
    commit_reveal_weights_enabled: bool = False
    alpha_high: float
    alpha_low: float
    liquid_alpha_enabled: bool
    validator_prune_len: int = 0
    scaling_law_power: int = 0
    synergy_scaling_law_power: int = 0
    subnetwork_n: int = 0
    max_allowed_uids: int = 0
    blocks_since_last_step: int = 0
    block_number: int = 0


class CallArgDTO(BaseModel):
    """Data transfer object for call arguments."""

    model_config = ConfigDict(frozen=True)

    name: str
    type: str
    value: int | str | dict | list | bool | None


class CallDTO(BaseModel):
    """Data transfer object for extrinsic call data."""

    model_config = ConfigDict(frozen=True)

    call_index: str
    call_function: str
    call_module: str
    call_args: list[CallArgDTO]
    call_hash: str


class ExtrinsicDTO(BaseModel):
    """Data transfer object for blockchain extrinsics."""

    model_config = ConfigDict(frozen=True)

    extrinsic_hash: str
    extrinsic_length: int
    call: CallDTO
    address: str | None = None
    signature: dict | None = None
    era: tuple[int, int] | str | None = None
    nonce: int | None = None
    tip: int | None = None
    mode: dict | None = None
