"""Bittensor blockchain provider using the Pylon client SDK."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import structlog
from pylon_client._internal.pylon_commons.types import ExtrinsicIndex
from pylon_client.artanis import BlockNumber, Config, NetUid, PylonAuthToken, PylonClient

from sentinel.v1.providers.base import BlockchainProvider

if TYPE_CHECKING:
    from bittensor.core.chain_data import SubnetHyperparameters
    from bittensor.core.metagraph import Metagraph
    from pylon_client.artanis.v1 import GetNeuronsResponse, Neuron

logger = structlog.get_logger()

DEFAULT_PYLON_URL = "http://localhost:8000"


class PylonProvider(BlockchainProvider):
    """Provider for interacting with the Bittensor blockchain via Pylon service."""

    def __init__(self, url: str, open_access_token: str | None = None) -> None:
        self._url = url
        self._open_access_token = open_access_token
        self._client: PylonClient | None = None
        self._block_hash_cache: dict[int, str] = {}

    def _get_client(self) -> PylonClient:
        if self._client is None:
            config = Config(
                address=self._url,
                open_access_token=PylonAuthToken(self._open_access_token or ""),
            )
            self._client = PylonClient(config)
            self._client.open()
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> PylonProvider:
        self._get_client()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def get_current_block(self) -> int:
        try:
            client = self._get_client()
            block_info = client.v1.open_access.get_latest_block_info()
            self._block_hash_cache[block_info.number] = block_info.hash
            return block_info.number
        except Exception:
            logger.exception("Failed to get current block")
            raise

    def get_block_hash(self, block_number: int) -> str | None:
        if block_number in self._block_hash_cache:
            return self._block_hash_cache[block_number]
        try:
            client = self._get_client()
            block_info = client.v1.open_access.get_latest_block_info()
            self._block_hash_cache[block_info.number] = block_info.hash
            if block_info.number == block_number:
                return block_info.hash
            # Pylon has no direct block-hash-by-number API;
            # use get_neurons on root subnet as a probe.
            response = client.v1.open_access.get_neurons(
                netuid=NetUid(0),
                block_number=BlockNumber(block_number),
            )
            block_hash = response.block.hash
            self._block_hash_cache[block_number] = block_hash
            return block_hash
        except Exception:
            logger.exception("Failed to get block hash", block_number=block_number)
            return None

    def get_block_info(
        self,
        block_number: int | None = None,
        block_hash: str | None = None,
    ) -> Any:
        """Pylon does not provide full block info. Returns None."""
        return None

    def get_events(self, block_hash: str) -> list[dict[str, Any]]:
        raise NotImplementedError("PylonProvider does not support get_events")

    def get_extrinsics(self, block_hash: str) -> list[dict[str, Any]] | None:
        raise NotImplementedError("PylonProvider does not support get_extrinsics")

    def get_extrinsic_events(self, block_hash: str) -> dict[int, list[dict[str, Any]]]:
        raise NotImplementedError("PylonProvider does not support get_extrinsic_events")

    def get_extrinsic_status(self, block_hash: str, extrinsic_index: int) -> tuple[str, dict[str, Any] | None]:
        raise NotImplementedError("PylonProvider does not support get_extrinsic_status")

    def get_subnet_hyperparams(self, block_number: int, netuid: int) -> list[Any] | SubnetHyperparameters | None:
        """Pylon does not provide subnet hyperparameters. Returns None."""
        return None

    def get_metagraph(
        self,
        netuid: int,
        block_number: int,
        mechid: int = 0,
        *,
        lite: bool = False,
    ) -> Metagraph | None:
        """
        Construct a Metagraph from Pylon neuron data.

        Always returns a lite metagraph (no weights/bonds).
        If lite=False is requested, a warning is logged.
        """
        if not lite:
            logger.warning(
                "PylonProvider can only provide lite metagraphs (no weights/bonds)",
                netuid=netuid,
                block_number=block_number,
            )

        try:
            client = self._get_client()
            response = client.v1.open_access.get_neurons(
                netuid=NetUid(netuid),
                block_number=BlockNumber(block_number),
            )
            self._block_hash_cache[response.block.number] = response.block.hash
            return self._build_metagraph(response, netuid, block_number, mechid)
        except Exception:
            logger.exception(
                "Failed to get metagraph",
                netuid=netuid,
                block_number=block_number,
            )
            return None

    def _build_metagraph(
        self,
        response: GetNeuronsResponse,
        netuid: int,
        block_number: int,
        mechid: int,
    ) -> Metagraph:
        from bittensor.core.chain_data import AxonInfo, NeuronInfoLite
        from bittensor.core.metagraph import Metagraph
        from bittensor.utils.balance import Balance

        neurons_lite = []
        for hotkey, neuron in sorted(response.neurons.items(), key=lambda item: item[1].uid):
            neurons_lite.append(
                NeuronInfoLite(
                    hotkey=str(hotkey),
                    coldkey=str(neuron.coldkey),
                    uid=neuron.uid,
                    netuid=netuid,
                    active=int(neuron.active),
                    stake=Balance.from_tao(float(neuron.stakes.total)),
                    stake_dict={str(neuron.coldkey): Balance.from_tao(float(neuron.stakes.total))},
                    total_stake=Balance.from_tao(float(neuron.stakes.total)),
                    rank=float(neuron.rank),
                    emission=float(neuron.emission),
                    incentive=float(neuron.incentive),
                    consensus=float(neuron.consensus),
                    trust=float(neuron.trust),
                    validator_trust=float(neuron.validator_trust),
                    dividends=float(neuron.dividends),
                    last_update=neuron.last_update,
                    validator_permit=bool(neuron.validator_permit),
                    pruning_score=neuron.pruning_score,
                    prometheus_info=None,
                    axon_info=AxonInfo(
                        version=0,
                        ip=str(neuron.axon_info.ip),
                        port=neuron.axon_info.port,
                        ip_type=4,
                        hotkey=str(hotkey),
                        coldkey=str(neuron.coldkey),
                        protocol=neuron.axon_info.protocol.value,
                    ),
                ),
            )

        metagraph = Metagraph(
            netuid=netuid,
            network="pylon",
            mechid=mechid,
            sync=False,
            lite=True,
        )
        metagraph.neurons = neurons_lite
        metagraph._set_metagraph_attributes(block_number)

        n = len(neurons_lite)
        metagraph.weights = metagraph._create_tensor(
            [[0.0] * n for _ in range(n)],
            dtype=metagraph._dtype_registry["float32"],
        )
        metagraph.bonds = metagraph._create_tensor(
            [[0.0] * n for _ in range(n)],
            dtype=metagraph._dtype_registry["float32"],
        )

        # Populate stake arrays (not set by _set_metagraph_attributes)
        sorted_neurons = [neuron for _, neuron in sorted(response.neurons.items(), key=lambda item: item[1].uid)]
        metagraph.alpha_stake = metagraph._create_tensor(
            [float(neuron.stakes.alpha) for neuron in sorted_neurons],
            dtype=metagraph._dtype_registry["float32"],
        )
        metagraph.tao_stake = metagraph._create_tensor(
            [float(neuron.stakes.tao) for neuron in sorted_neurons],
            dtype=metagraph._dtype_registry["float32"],
        )
        metagraph.total_stake = metagraph.stake = metagraph._create_tensor(
            [float(neuron.stakes.total) for neuron in sorted_neurons],
            dtype=metagraph._dtype_registry["float32"],
        )

        return metagraph

    def get_mechanism_count(self, netuid: int) -> int:
        logger.warning(
            "PylonProvider does not have mechanism count API, defaulting to 1",
            netuid=netuid,
        )
        return 1

    # --- Pylon-specific methods (not in base interface) ---

    def get_neurons(self, netuid: int, block_number: int) -> dict[str, Any]:
        """Get neurons for a subnet at a specific block."""
        try:
            client = self._get_client()
            response = client.v1.open_access.get_neurons(
                netuid=NetUid(netuid),
                block_number=BlockNumber(block_number),
            )
            self._block_hash_cache[response.block.number] = response.block.hash
            return self._serialize_neurons_response(response)
        except Exception:
            logger.exception("Failed to get neurons", netuid=netuid, block_number=block_number)
            raise

    def get_latest_neurons(self, netuid: int) -> dict[str, Any]:
        """Get neurons for a subnet at the latest block."""
        try:
            client = self._get_client()
            response = client.v1.open_access.get_latest_neurons(netuid=NetUid(netuid))
            self._block_hash_cache[response.block.number] = response.block.hash
            return self._serialize_neurons_response(response)
        except Exception:
            logger.exception("Failed to get latest neurons", netuid=netuid)
            raise

    def get_validators(self, netuid: int, block_number: int) -> list[dict[str, Any]]:
        """Get validators for a subnet at a specific block."""
        try:
            client = self._get_client()
            response = client.v1.open_access.get_validators(
                netuid=NetUid(netuid),
                block_number=BlockNumber(block_number),
            )
            return [self._serialize_neuron(v) for v in response.validators]
        except Exception:
            logger.exception("Failed to get validators", netuid=netuid, block_number=block_number)
            raise

    def get_extrinsic_by_index(self, block_number: int, extrinsic_index: int) -> dict[str, Any] | None:
        """Get a specific extrinsic by block number and index."""
        try:
            client = self._get_client()
            response = client.v1.open_access.get_extrinsic(
                block_number=BlockNumber(block_number),
                extrinsic_index=ExtrinsicIndex(extrinsic_index),
            )
            return {
                "block_number": response.block_number,
                "index": response.extrinsic_index,
                "extrinsic_hash": response.extrinsic_hash,
                "extrinsic_length": response.extrinsic_length,
                "address": response.address,
                "call_module": response.call.call_module,
                "call_function": response.call.call_function,
                "call_args": [
                    {"name": arg.name, "type": arg.type, "value": arg.value} for arg in response.call.call_args
                ],
            }
        except Exception:
            logger.exception(
                "Failed to get extrinsic",
                block_number=block_number,
                extrinsic_index=extrinsic_index,
            )
            return None

    # --- Private helpers ---

    @staticmethod
    def _serialize_neuron(neuron: Neuron) -> dict[str, Any]:
        return {
            "uid": neuron.uid,
            "hotkey": neuron.hotkey,
            "coldkey": neuron.coldkey,
            "active": neuron.active,
            "stake": neuron.stake,
            "rank": neuron.rank,
            "emission": neuron.emission,
            "incentive": neuron.incentive,
            "consensus": neuron.consensus,
            "trust": neuron.trust,
            "validator_trust": neuron.validator_trust,
            "dividends": neuron.dividends,
            "last_update": neuron.last_update,
            "validator_permit": neuron.validator_permit,
            "pruning_score": neuron.pruning_score,
            "axon_info": {
                "ip": str(neuron.axon_info.ip),
                "port": neuron.axon_info.port,
                "protocol": neuron.axon_info.protocol.value,
            },
            "stakes": {
                "alpha": neuron.stakes.alpha,
                "tao": neuron.stakes.tao,
                "total": neuron.stakes.total,
            },
        }

    def _serialize_neurons_response(self, response: GetNeuronsResponse) -> dict[str, Any]:
        return {
            "block": {"number": response.block.number, "hash": response.block.hash},
            "neurons": {hotkey: self._serialize_neuron(neuron) for hotkey, neuron in response.neurons.items()},
        }


def pylon_provider(
    url: str | None = None,
    open_access_token: str | None = None,
) -> PylonProvider:
    """
    Factory function to create a PylonProvider instance.

    Args:
        url: The Pylon service URL. If not provided, reads from
             PYLON_URL environment variable or uses default.
        open_access_token: Token for Pylon open access API. If not provided,
                          reads from PYLON_OPEN_ACCESS_TOKEN environment variable.

    Returns:
        PylonProvider instance

    """
    addr = url or os.getenv("PYLON_URL") or DEFAULT_PYLON_URL
    token = open_access_token or os.getenv("PYLON_OPEN_ACCESS_TOKEN")
    return PylonProvider(addr, open_access_token=token)
