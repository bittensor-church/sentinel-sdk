from pydantic import BaseModel, ConfigDict, computed_field


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

    call_index: str | None = None
    call_function: str
    call_module: str
    call_args: list[CallArgDTO]
    call_hash: str | None = None


class EventDataDTO(BaseModel):
    """Data transfer object for nested event data."""

    model_config = ConfigDict(frozen=True)

    event_index: str | int
    module_id: str
    event_id: str
    attributes: dict | tuple | list | str | None = None


class EventDTO(BaseModel):
    """Data transfer object for blockchain events."""

    model_config = ConfigDict(frozen=True)

    phase: str | dict
    extrinsic_idx: int | None
    event: EventDataDTO | None = None
    event_index: str | int
    module_id: str
    event_id: str
    attributes: dict | tuple | list | str | None = None
    topics: list | None = None


class ExtrinsicDTO(BaseModel):
    """Data transfer object for blockchain extrinsics."""

    model_config = ConfigDict(frozen=True)

    index: int
    extrinsic_hash: str | None = None
    call: CallDTO
    address: str | None = None
    signature: dict | None = None
    nonce: int | None = None
    tip: int | None = None
    events: list[EventDTO] | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> str | None:
        """Get extrinsic status from the last event."""
        if not self.events:
            return None
        last_event = self.events[-1]
        if last_event.module_id == "System" and last_event.event_id == "ExtrinsicSuccess":
            return "success"
        if last_event.module_id == "System" and last_event.event_id == "ExtrinsicFailed":
            return "failed"
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def netuid(self) -> int | None:
        """Extract netuid from call arguments if present."""
        for arg in self.call.call_args:
            if arg.name == "netuid":
                if isinstance(arg.value, int):
                    return arg.value
                if isinstance(arg.value, str):
                    try:
                        return int(arg.value)
                    except ValueError:
                        return None
        return None


# TODO: Determine if this DTO is necessary or can be removed
class SubnetInfoDTO(BaseModel):
    """Data transfer object for subnet information."""

    model_config = ConfigDict(frozen=True)

    netuid: int
    block_number: int
    info: dict | str | None = None
