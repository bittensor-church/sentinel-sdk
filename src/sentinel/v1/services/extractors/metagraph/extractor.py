from bittensor.core.chain_data import MetagraphInfo
from bittensor.core.subtensor import Subtensor


class MetagraphExtractor:
    def __init__(self, subtensor: Subtensor, block_number: int, netuid: int, mech_id: int = 0) -> None:
        self.subtensor = subtensor
        self.block_number = block_number
        self.netuid = netuid
        self.mech_id = mech_id

    def extract(self) -> MetagraphInfo | None:
        """
        Extract metagraph for the given block number and netuid.
        """
        return self.subtensor.get_metagraph_info(netuid=self.netuid, block=self.block_number, mechid=self.mech_id)
