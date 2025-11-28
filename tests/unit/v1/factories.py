import random

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

import sentinel.v1.dto as sentinel_dto
from sentinel.v1.services.extractors.extrinsics.filters import HYPERPARAM_FUNCTIONS


class HyperparametersDTOFactory(ModelFactory[sentinel_dto.HyperparametersDTO]): ...


class CallArgDTOFactory(ModelFactory[sentinel_dto.CallArgDTO]): ...


class CallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    call_args = Use(lambda: CallArgDTOFactory.batch(3))


class ExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    call = Use(lambda: CallDTOFactory.build())


class EventDataDTOFactory(ModelFactory[sentinel_dto.EventDataDTO]): ...


class EventDTOFactory(ModelFactory[sentinel_dto.EventDTO]):
    event = Use(lambda: EventDataDTOFactory.build())


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
        """Build an extrinsic for a specific hyperparam function.

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
