"""Extrinsic filtering utilities for hyperparameter changes."""

import structlog

from sentinel.v1.dto import CallDTO, ExtrinsicDTO

logger = structlog.get_logger()

# Modules that can contain hyperparameter changes
HYPERPARAM_MODULES = {"AdminUtils", "SubtensorModule"}

# Complete list of hyperparameter-changing functions
HYPERPARAM_FUNCTIONS = {
    # Consensus & Weights
    "sudo_set_rho",
    "sudo_set_kappa",
    "sudo_set_tempo",
    "sudo_set_weights_version_key",
    "sudo_set_weights_set_rate_limit",
    "sudo_set_max_weight_limit",
    "sudo_set_min_allowed_weights",
    "sudo_set_bonds_moving_average",
    "sudo_set_bonds_reset_enabled",
    # Commit-Reveal
    "sudo_set_commit_reveal_weights_enabled",
    "sudo_set_commit_reveal_period",
    # Alpha Parameters
    "sudo_set_alpha_values",
    "sudo_set_liquid_alpha_enabled",
    "sudo_set_alpha_sigmoid_steepness",
    # Registration
    "sudo_set_network_registration_allowed",
    "sudo_set_target_registrations_per_interval",
    "sudo_set_max_registrations_per_block",
    "sudo_set_immunity_period",
    # Difficulty & Burn
    "sudo_set_difficulty",
    "sudo_set_min_difficulty",
    "sudo_set_max_difficulty",
    "sudo_set_min_burn",
    "sudo_set_max_burn",
    "sudo_set_adjustment_alpha",
    "sudo_set_adjustment_interval",
    # Validator
    "sudo_set_max_allowed_validators",
    "sudo_set_activity_cutoff",
    "sudo_set_serving_rate_limit",
    # Subnet State
    "sudo_set_transfers_enabled",
    "sudo_set_user_liquidity_enabled",
    "sudo_set_yuma_version",
    # Global Parameters
    "sudo_set_admin_freeze_window",
    "sudo_set_network_rate_limit",
    "sudo_set_tx_rate_limit",
    "sudo_set_lock_reduction_interval",
    "sudo_set_nominator_min_required_stake",
    "sudo_set_stake_threshold",
    "sudo_set_tx_delegate_take_rate_limit",
    "sudo_set_network_pow_registration_allowed",
    # Mechanism
    "sudo_set_mechanism_count",
    "sudo_set_mechanism_emission_split",
}

# Sudo modules that wrap hyperparam calls
SUDO_MODULES = {"Sudo"}
SUDO_FUNCTIONS = {"sudo", "sudo_unchecked_weight", "sudo_as"}


def _is_hyperparam_call(call: CallDTO) -> bool:
    """Check if a call is a direct hyperparameter change."""
    if call.call_module not in HYPERPARAM_MODULES:
        return False
    return call.call_function in HYPERPARAM_FUNCTIONS


def _extract_nested_call(call: CallDTO) -> CallDTO | None:
    """Extract nested call from sudo wrapper."""
    for arg in call.call_args:
        if arg.name == "call" and isinstance(arg.value, dict):
            try:
                return CallDTO.model_validate(arg.value)
            except Exception:
                return None
    return None


def is_hyperparam_extrinsic(ext: ExtrinsicDTO) -> bool:
    """
    Check if an extrinsic contains a hyperparameter change.

    This checks both direct calls and calls wrapped in Sudo.

    Args:
        ext: The extrinsic to check

    Returns:
        True if the extrinsic modifies hyperparameters

    """
    # Direct hyperparam call
    if _is_hyperparam_call(ext.call):
        return True

    # Check if it's a sudo-wrapped call
    if ext.call.call_module in SUDO_MODULES and ext.call.call_function in SUDO_FUNCTIONS:
        nested = _extract_nested_call(ext.call)
        if nested and _is_hyperparam_call(nested):
            return True

    return False


def get_hyperparam_info(ext: ExtrinsicDTO) -> dict | None:
    """
    Extract hyperparameter change info from an extrinsic.

    Args:
        ext: The extrinsic to extract info from

    Returns:
        Dict with function, module, netuid, and params if it's a hyperparam change,
        None otherwise

    """
    call = ext.call

    # Handle sudo wrapper
    if call.call_module in SUDO_MODULES and call.call_function in SUDO_FUNCTIONS:
        nested = _extract_nested_call(call)
        if nested:
            call = nested

    if not _is_hyperparam_call(call):
        return None

    info: dict = {
        "function": call.call_function,
        "module": call.call_module,
        "params": {},
    }

    for arg in call.call_args:
        if arg.name == "netuid":
            info["netuid"] = arg.value
        else:
            info["params"][arg.name] = arg.value

    return info


def filter_hyperparam_extrinsics(extrinsics: list[ExtrinsicDTO]) -> list[ExtrinsicDTO]:
    """
    Filter a list of extrinsics to only include hyperparameter changes.

    Args:
        extrinsics: List of extrinsics to filter

    Returns:
        List containing only hyperparameter-changing extrinsics

    """
    return [ext for ext in extrinsics if is_hyperparam_extrinsic(ext)]


def filter_weight_set_extrinsics(extrinsics: list[ExtrinsicDTO]) -> list[ExtrinsicDTO]:
    """
    Filter extrinsics to only include weight set changes.

    Args:
        extrinsics: List of extrinsics to filter

    Returns:
        List containing only weight set changing extrinsics

    """
    weight_set_functions = {
        "set_weights",
    }
    return [ext for ext in extrinsics if ext.call.call_function in weight_set_functions]


def filter_timestamp_extrinsic(extrinsics: list[ExtrinsicDTO]) -> list[ExtrinsicDTO]:
    """
    Filter extrinsics to only include timestamp set calls.

    Args:
        extrinsics: List of extrinsics to filter

    Returns:
        List containing only timestamp extrinsics

    """
    return [ext for ext in extrinsics if ext.call.call_module == "Timestamp" and ext.call.call_function == "set"]
