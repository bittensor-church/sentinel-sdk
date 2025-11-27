### Extrinsic Call Flow

```
1. Compose inner call  →  AdminUtils module + function + params
2. Wrap in Sudo        →  Sudo.sudo(inner_call)
3. Sign with coldkey   →  wallet.coldkey
4. Submit extrinsic    →  substrate.submit_extrinsic()
5. Wait for finalization
```

## Subnet Hyperparameters Table

### Consensus & Weights Parameters

| Hyperparameter | Type | Extrinsic Function | Call Params | Description |
|----------------|------|-------------------|-------------|-------------|
| `rho` | `int` | `sudo_set_rho` | `{"netuid": int, "rho": int}` | Rate of decay |
| `kappa` | `int` | `sudo_set_kappa` | `{"netuid": int, "kappa": int}` | Constant multiplier in calculations |
| `tempo` | `int` | `sudo_set_tempo` | `{"netuid": int, "tempo": int}` | Blocks per epoch |
| `weights_version` | `int` | `sudo_set_weights_version_key` | `{"netuid": int, "weights_version_key": int}` | Version number of weights |
| `weights_rate_limit` | `int` | `sudo_set_weights_set_rate_limit` | `{"netuid": int, "weights_set_rate_limit": int}` | Rate limit for weight updates |
| `max_weight_limit` | `float` | `sudo_set_max_weight_limit` | `{"netuid": int, "max_weight_limit": int}` | Maximum weight limit |
| `min_allowed_weights` | `int` | `sudo_set_min_allowed_weights` | `{"netuid": int, "min_allowed_weights": int}` | Minimum allowed weights |
| `bonds_moving_avg` | `int` | `sudo_set_bonds_moving_average` | `{"netuid": int, "bonds_moving_average": int}` | Moving average of bonds |
| `bonds_reset_enabled` | `bool` | `sudo_set_bonds_reset_enabled` | `{"netuid": int, "enabled": bool}` | Flag for bonds reset |

### Commit-Reveal Weights

| Hyperparameter | Type | Extrinsic Function | Call Params | Description |
|----------------|------|-------------------|-------------|-------------|
| `commit_reveal_weights_enabled` | `bool` | `sudo_set_commit_reveal_weights_enabled` | `{"netuid": int, "enabled": bool}` | Enable/disable commit-reveal |
| `commit_reveal_period` | `int` | `sudo_set_commit_reveal_period` | `{"netuid": int, "commit_reveal_period": int}` | Commit-reveal interval in blocks |

### Alpha Parameters (Liquid Alpha)

| Hyperparameter | Type | Extrinsic Function | Call Params | Description |
|----------------|------|-------------------|-------------|-------------|
| `alpha_high` | `int` | `sudo_set_alpha_values` | `{"netuid": int, "alpha_low": int, "alpha_high": int}` | High alpha value |
| `alpha_low` | `int` | `sudo_set_alpha_values` | `{"netuid": int, "alpha_low": int, "alpha_high": int}` | Low alpha value |
| `liquid_alpha_enabled` | `bool` | `sudo_set_liquid_alpha_enabled` | `{"netuid": int, "enabled": bool}` | Enable liquid alpha |
| `alpha_sigmoid_steepness` | `float` | `sudo_set_alpha_sigmoid_steepness` | `{"netuid": int, "alpha_sigmoid_steepness": int}` | Sigmoid steepness for alpha |

### Registration Parameters

| Hyperparameter | Type | Extrinsic Function | Call Params | Description |
|----------------|------|-------------------|-------------|-------------|
| `registration_allowed` | `bool` | `sudo_set_network_registration_allowed` | `{"netuid": int, "registration_allowed": bool}` | Allow registration on subnet |
| `target_regs_per_interval` | `int` | `sudo_set_target_registrations_per_interval` | `{"netuid": int, "target_registrations_per_interval": int}` | Target registrations per interval |
| `max_regs_per_block` | `int` | `sudo_set_max_registrations_per_block` | `{"netuid": int, "max_registrations_per_block": int}` | Max registrations per block |
| `immunity_period` | `int` | `sudo_set_immunity_period` | `{"netuid": int, "immunity_period": int}` | Immunity period duration |

### Difficulty & Burn Parameters

| Hyperparameter | Type | Extrinsic Function | Call Params | Description |
|----------------|------|-------------------|-------------|-------------|
| `difficulty` | `int` | `sudo_set_difficulty` | `{"netuid": int, "difficulty": int}` | Current difficulty level |
| `min_difficulty` | `int` | `sudo_set_min_difficulty` | `{"netuid": int, "min_difficulty": int}` | Minimum difficulty |
| `max_difficulty` | `int` | `sudo_set_max_difficulty` | `{"netuid": int, "max_difficulty": int}` | Maximum difficulty |
| `min_burn` | `int` | `sudo_set_min_burn` | `{"netuid": int, "min_burn": int}` | Minimum burn value |
| `max_burn` | `int` | `sudo_set_max_burn` | `{"netuid": int, "max_burn": int}` | Maximum burn value |
| `adjustment_alpha` | `int` | `sudo_set_adjustment_alpha` | `{"netuid": int, "adjustment_alpha": int}` | Alpha for adjustments |
| `adjustment_interval` | `int` | `sudo_set_adjustment_interval` | `{"netuid": int, "adjustment_interval": int}` | Adjustment interval |

### Validator Parameters

| Hyperparameter | Type | Extrinsic Function | Call Params | Description |
|----------------|------|-------------------|-------------|-------------|
| `max_validators` | `int` | `sudo_set_max_allowed_validators` | `{"netuid": int, "max_allowed_validators": int}` | Maximum validators |
| `activity_cutoff` | `int` | `sudo_set_activity_cutoff` | `{"netuid": int, "activity_cutoff": int}` | Activity cutoff threshold |
| `serving_rate_limit` | `int` | `sudo_set_serving_rate_limit` | `{"netuid": int, "serving_rate_limit": int}` | Serving rate limit |

### Subnet State Parameters

| Hyperparameter | Type | Extrinsic Function | Call Params | Description |
|----------------|------|-------------------|-------------|-------------|
| `subnet_is_active` | `bool` | N/A (set by START CALL) | N/A | Subnet active status |
| `transfers_enabled` | `bool` | `sudo_set_transfers_enabled` | `{"netuid": int, "enabled": bool}` | Enable transfers |
| `user_liquidity_enabled` | `bool` | `sudo_set_user_liquidity_enabled` | `{"netuid": int, "enabled": bool}` | Enable user liquidity |
| `yuma_version` | `int` | `sudo_set_yuma_version` | `{"netuid": int, "yuma_version": int}` | Yuma consensus version |

## Global (Non-Subnet) Parameters

These parameters are set globally, not per-subnet:

| Parameter | Extrinsic Function | Call Params | Description |
|-----------|-------------------|-------------|-------------|
| Admin Freeze Window | `sudo_set_admin_freeze_window` | `{"window": int}` | Freeze window at end of tempo |
| Network Rate Limit | `sudo_set_network_rate_limit` | `{"rate_limit": int}` | Global network rate limit |
| TX Rate Limit | `sudo_set_tx_rate_limit` | `{"rate_limit": int}` | Transaction rate limit |
| Lock Reduction Interval | `sudo_set_lock_reduction_interval` | `{"interval": int}` | Lock reduction interval |
| Nominator Min Stake | `sudo_set_nominator_min_required_stake` | `{"stake": int}` | Minimum nominator stake |
| Stake Threshold | `sudo_set_stake_threshold` | `{"stake_threshold": int}` | Stake threshold |
| Delegate Take Rate Limit | `sudo_set_tx_delegate_take_rate_limit` | `{"rate_limit": int}` | Delegate take rate limit |
| POW Registration | `sudo_set_network_pow_registration_allowed` | `{"netuid": int, "enabled": bool}` | Allow POW registration |

## Mechanism Parameters

Special parameters for subnet mechanisms:

| Parameter | Extrinsic Function | Call Params | Description |
|-----------|-------------------|-------------|-------------|
| Mechanism Count | `sudo_set_mechanism_count` | `{"netuid": int, "mechanism_count": int}` | Number of subnet mechanisms |
| Mechanism Emission Split | `sudo_set_mechanism_emission_split` | `{"netuid": int, "maybe_split": list[int]}` | Emission distribution ratio |