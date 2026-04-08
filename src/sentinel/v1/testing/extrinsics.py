"""Domain-specific extrinsic preset factories."""

import random

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

import sentinel.v1.dto as sentinel_dto
from sentinel.v1.services.extractors.extrinsics.filters import HYPERPARAM_FUNCTIONS

# Default SS58 addresses and hashes used as factory defaults
_DEFAULT_COLDKEY_HASH = "0xd177d32e9426098c20528cf328730a319c790264e2510754c4e2a756d5b6e32a"
_DEFAULT_NEW_COLDKEY = "5CHuuWaMucXwaLqjM4jsvAp9NvrxMpavus1dBMsCEiqvRtNU"
_DEFAULT_COLDKEY = "5GKYVYof1CbEuNcnBSa2wXx3rs5StYYVBPdg8C5CQ8MifCBc"
_DEFAULT_HOTKEY = "5Eh5G8BD8NVHfqeWdKhNbrssDKKV8B74a2VghHzr2YYWrwmK"
_DEFAULT_HOTKEY_2 = "5EEinUEy3cfBCUyhbvCcYfWU713QCsDoVXqbbRLKFtEqKkC9"

# Hyperparameter extrinsics


class HyperparamCallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    """Factory for creating hyperparameter-setting call DTOs."""

    call_module = "AdminUtils"
    call_function = Use(lambda: random.choice(list(HYPERPARAM_FUNCTIONS)))
    call_args = Use(
        lambda: [
            sentinel_dto.CallArgDTO(name="netuid", type="u16", value=1),
        ],
    )


class HyperparamExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    """Factory for creating hyperparameter-setting extrinsic DTOs."""

    call = Use(lambda: HyperparamCallDTOFactory.build())

    @classmethod
    def build_for_function(
        cls,
        function: str,
        netuid: int = 1,
        **param_values,
    ) -> sentinel_dto.ExtrinsicDTO:
        """
        Build an extrinsic for a specific hyperparam function.

        Args:
            function: The hyperparam function name (e.g., "sudo_set_tempo")
            netuid: The subnet ID
            **param_values: Parameter name/value pairs (e.g., tempo=360)

        """
        call_args = [sentinel_dto.CallArgDTO(name="netuid", type="u16", value=netuid)]
        for name, value in param_values.items():
            arg_type = "bool" if isinstance(value, bool) else "u64"
            call_args.append(sentinel_dto.CallArgDTO(name=name, type=arg_type, value=value))

        call = HyperparamCallDTOFactory.build(
            call_function=function,
            call_args=call_args,
        )
        return cls.build(call=call)


# Announce coldkey swap extrinsics


class AnnounceColdkeySwapCallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    """Factory for creating announce_coldkey_swap call DTOs."""

    call_module = "SubtensorModule"
    call_function = "announce_coldkey_swap"
    call_args = Use(
        lambda: [
            sentinel_dto.CallArgDTO(name="new_coldkey_hash", type="Hash", value=_DEFAULT_COLDKEY_HASH),
        ],
    )


class AnnounceColdkeySwapExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    """Factory for creating announce_coldkey_swap extrinsic DTOs."""

    call = Use(lambda: AnnounceColdkeySwapCallDTOFactory.build())

    @classmethod
    def build_for_hash(
        cls,
        new_coldkey_hash: str,
        **kwargs,
    ) -> sentinel_dto.ExtrinsicDTO:
        """
        Build an announce coldkey swap extrinsic for a specific hash.

        Args:
            new_coldkey_hash: The hash of the new coldkey
            **kwargs: Additional overrides for the extrinsic

        """
        call = AnnounceColdkeySwapCallDTOFactory.build(
            call_args=[
                sentinel_dto.CallArgDTO(name="new_coldkey_hash", type="Hash", value=new_coldkey_hash),
            ],
        )
        return cls.build(call=call, **kwargs)


# Coldkey swap extrinsics


class ColdkeySwapCallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    """Factory for creating swap_coldkey_announced call DTOs."""

    call_module = "SubtensorModule"
    call_function = "swap_coldkey_announced"
    call_args = Use(
        lambda: [
            sentinel_dto.CallArgDTO(name="new_coldkey", type="AccountId", value=_DEFAULT_NEW_COLDKEY),
        ],
    )


class ColdkeySwapExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    """Factory for creating swap_coldkey_announced extrinsic DTOs."""

    call = Use(lambda: ColdkeySwapCallDTOFactory.build())

    @classmethod
    def build_for_coldkey(
        cls,
        new_coldkey: str,
        **kwargs,
    ) -> sentinel_dto.ExtrinsicDTO:
        """
        Build a coldkey swap extrinsic for a specific new coldkey.

        Args:
            new_coldkey: The SS58-encoded destination coldkey address
            **kwargs: Additional overrides for the extrinsic

        """
        call = ColdkeySwapCallDTOFactory.build(
            call_args=[
                sentinel_dto.CallArgDTO(name="new_coldkey", type="AccountId", value=new_coldkey),
            ],
        )
        return cls.build(call=call, **kwargs)


# Coldkey swap dispute extrinsics


class DisputeColdkeySwapCallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    """Factory for creating dispute_coldkey_swap call DTOs."""

    call_module = "SubtensorModule"
    call_function = "dispute_coldkey_swap"
    call_args: list = []


class DisputeColdkeySwapExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    """Factory for creating dispute_coldkey_swap extrinsic DTOs."""

    call = Use(lambda: DisputeColdkeySwapCallDTOFactory.build())


# Clear coldkey swap announcement extrinsics


class ClearColdkeySwapCallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    """Factory for creating clear_coldkey_swap_announcement call DTOs."""

    call_module = "SubtensorModule"
    call_function = "clear_coldkey_swap_announcement"
    call_args: list = []


class ClearColdkeySwapExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    """Factory for creating clear_coldkey_swap_announcement extrinsic DTOs."""

    call = Use(lambda: ClearColdkeySwapCallDTOFactory.build())


# Reset coldkey swap extrinsics


class ResetColdkeySwapCallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    """Factory for creating reset_coldkey_swap call DTOs."""

    call_module = "SubtensorModule"
    call_function = "reset_coldkey_swap"
    call_args = Use(
        lambda: [
            sentinel_dto.CallArgDTO(name="coldkey", type="AccountId", value=_DEFAULT_COLDKEY),
        ],
    )


class ResetColdkeySwapExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    """Factory for creating reset_coldkey_swap extrinsic DTOs."""

    call = Use(lambda: ResetColdkeySwapCallDTOFactory.build())

    @classmethod
    def build_for_coldkey(
        cls,
        coldkey: str,
        **kwargs,
    ) -> sentinel_dto.ExtrinsicDTO:
        """
        Build a reset coldkey swap extrinsic for a specific coldkey.

        Args:
            coldkey: The SS58-encoded coldkey address to reset
            **kwargs: Additional overrides for the extrinsic

        """
        call = ResetColdkeySwapCallDTOFactory.build(
            call_args=[
                sentinel_dto.CallArgDTO(name="coldkey", type="AccountId", value=coldkey),
            ],
        )
        return cls.build(call=call, **kwargs)


# Register network extrinsics


def _random_subnet_identity() -> dict[str, str]:
    """Generate a realistic-looking random subnet identity."""
    fake = _get_faker()
    word = fake.word().capitalize()
    suffix = random.choice(["AI", "Net", "Labs", "Protocol", "Network", "Intelligence"])
    subnet_name = f"{word}{suffix}"
    github_user = fake.user_name()
    return {
        "subnet_name": subnet_name,
        "github_repo": f"https://github.com/{github_user}/{subnet_name.lower()}",
        "subnet_contact": f"@{github_user}",
        "subnet_url": f"https://{subnet_name.lower()}.io",
        "discord": f"https://discord.gg/{fake.lexify('????????')}",
        "description": f"{subnet_name} - {fake.bs()}",
        "logo_url": f"https://{subnet_name.lower()}.io/logo.png",
        "additional": "",
    }


def _get_faker():
    try:
        from faker import Faker
    except ImportError:
        return _FallbackFaker()
    return Faker()


class _FallbackFaker:
    """Minimal faker fallback when Faker is not installed."""

    _counter = 0

    def word(self) -> str:
        _FallbackFaker._counter += 1
        words = ["Alpha", "Beta", "Gamma", "Delta", "Sigma", "Omega", "Nova", "Pixel", "Nexus", "Cortex"]
        return words[_FallbackFaker._counter % len(words)]

    def user_name(self) -> str:
        return f"user{random.randint(100, 9999)}"

    def bs(self) -> str:
        phrases = [
            "decentralized inference network",
            "distributed compute protocol",
            "on-chain machine learning",
            "neural consensus layer",
            "incentivized data pipeline",
        ]
        return random.choice(phrases)

    def lexify(self, pattern: str) -> str:
        return "".join(random.choice("abcdefghijklmnopqrstuvwxyz") if c == "?" else c for c in pattern)


class RegisterNetworkCallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    """Factory for creating register_network call DTOs."""

    call_module = "SubtensorModule"
    call_function = "register_network"
    call_args = Use(
        lambda: [
            sentinel_dto.CallArgDTO(name="hotkey", type="AccountId", value=_DEFAULT_HOTKEY),
        ],
    )


class RegisterNetworkExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    """Factory for creating register_network extrinsic DTOs."""

    call = Use(lambda: RegisterNetworkCallDTOFactory.build())

    @classmethod
    def build_for_hotkey(
        cls,
        hotkey: str,
        **kwargs,
    ) -> sentinel_dto.ExtrinsicDTO:
        """
        Build a register network extrinsic for a specific hotkey.

        Args:
            hotkey: The SS58-encoded hotkey address
            **kwargs: Additional overrides for the extrinsic

        """
        call = RegisterNetworkCallDTOFactory.build(
            call_args=[
                sentinel_dto.CallArgDTO(name="hotkey", type="AccountId", value=hotkey),
            ],
        )
        return cls.build(call=call, **kwargs)


class RegisterNetworkWithIdentityCallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    """Factory for creating register_network_with_identity call DTOs."""

    call_module = "SubtensorModule"
    call_function = "register_network_with_identity"
    call_args = Use(
        lambda: [
            sentinel_dto.CallArgDTO(
                name="hotkey",
                type="AccountId",
                value=_DEFAULT_HOTKEY_2,
            ),
            sentinel_dto.CallArgDTO(
                name="identity",
                type="Option<SubnetIdentityOfV3>",
                value=_random_subnet_identity(),
            ),
        ],
    )


class RegisterNetworkWithIdentityExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    """Factory for creating register_network_with_identity extrinsic DTOs."""

    call = Use(lambda: RegisterNetworkWithIdentityCallDTOFactory.build())

    @classmethod
    def build_for_hotkey(
        cls,
        hotkey: str,
        subnet_name: str = "",
        **kwargs,
    ) -> sentinel_dto.ExtrinsicDTO:
        """
        Build a register network with identity extrinsic.

        Args:
            hotkey: The SS58-encoded hotkey address
            subnet_name: The subnet name
            **kwargs: Additional overrides for the extrinsic

        """
        identity = {**_random_subnet_identity(), "subnet_name": subnet_name}
        call = RegisterNetworkWithIdentityCallDTOFactory.build(
            call_args=[
                sentinel_dto.CallArgDTO(name="hotkey", type="AccountId", value=hotkey),
                sentinel_dto.CallArgDTO(name="identity", type="Option<SubnetIdentityOfV3>", value=identity),
            ],
        )
        return cls.build(call=call, **kwargs)
