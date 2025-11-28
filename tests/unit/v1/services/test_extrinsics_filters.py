from sentinel.v1.services.extractors.extrinsics.extractor import ExtrinsicExtractor
from sentinel.v1.services.extractors.extrinsics.filters import filter_hyperparam_extrinsics
from tests.unit.v1.factories import HyperparamExtrinsicDTOFactory
from tests.unit.v1.providers import FakeBittensorProvider


def test_hyperparam_extrinsics(fake_provider: FakeBittensorProvider):
    block_number = 100
    block_hash = "0xabc123"

    extrinsics = [
        HyperparamExtrinsicDTOFactory.build_for_function(
            "sudo_set_rho",
            netuid=5,
            rho=100,
        ),
        HyperparamExtrinsicDTOFactory.build_for_function(
            "sudo_set_alpha_values",
            netuid=1,
            alpha_low=100,
            alpha_high=900,
        ),
    ]
    fake_provider.with_block(block_number, block_hash).with_extrinsics(
        block_hash,
        [ext.model_dump() for ext in extrinsics],
    )

    extractor = ExtrinsicExtractor(fake_provider, block_number=block_number)
    extractor_output = extractor.extract()
    assert len(extractor_output) == len(extrinsics)


def test_extrinsics_filter_hyperparam_only(fake_provider: FakeBittensorProvider):
    block_number = 200
    block_hash = "0xdef456"

    hyperparam_extrinsic = HyperparamExtrinsicDTOFactory.build_for_function(
        "sudo_set_rho",
        netuid=10,
        rho=250,
    )
    other_extrinsic = HyperparamExtrinsicDTOFactory.build_for_function(
        "some_other_function",
        param1=123,
        param2=456,
    )

    fake_provider.with_block(block_number, block_hash).with_extrinsics(
        block_hash,
        [
            hyperparam_extrinsic.model_dump(),
            other_extrinsic.model_dump(),
        ],
    )

    extractor = ExtrinsicExtractor(fake_provider, block_number=block_number)
    extractor_output = extractor.extract()

    # Filter only hyperparameter-related extrinsics
    hyperparam_extrinsics = [ext for ext in extractor_output if ext.call.call_function.startswith("sudo_set_")]

    assert len(hyperparam_extrinsics) == 1
    assert hyperparam_extrinsics[0].call.call_function == "sudo_set_rho"


def test_extrinsics_filter(fake_provider: FakeBittensorProvider, extrinsics_response):
    block_number = 300
    block_hash = "0xghi789"

    fake_provider.with_block(block_number, block_hash).with_extrinsics(
        block_hash,
        extrinsics_response,
    )

    extractor = ExtrinsicExtractor(fake_provider, block_number=block_number)
    extractor_output = extractor.extract()

    hyperparam_extrinsics = filter_hyperparam_extrinsics(extractor_output)

    assert len(hyperparam_extrinsics) == 2
