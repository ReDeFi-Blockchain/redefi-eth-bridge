import typing
import random

from .base import Worker, WorkerConfig
from src import util


__all__ = ['Signer']


class Signer(Worker):
    class SignerException(Exception):
        def __init__(self, message: str):
            self.message = message

    class SignerError(SignerException):
        pass

    def __init__(self, config: WorkerConfig = None):
        super().__init__(config)
        self.bridge = self.get_bridge_contract(
            self.api, self.config.eth_contract_address, poll_latency=self.config.poll_latency
        )
        self.chain_id = int(self.api.eth.chain_id)

    def list_by_event(self, event):
        tx_hash = event['transactionHash'].hex()
        deposit_event = event['args']
        if not self.bridge.call_method('hasPair', (deposit_event['token'], deposit_event['targetChainId'],)):
            raise self.SignerError(f'txHash {tx_hash}: pair for token {deposit_event["token"]} not registered')
        target_asset = self.bridge.call_method(
            'getDestinationAddress', (deposit_event['token'], deposit_event['targetChainId'])
        )

        # check link to targetChainId
        target_bridge_address = self.bridge.call_method('links', (deposit_event['targetChainId'],))
        if target_bridge_address == util.ADDRESS_0:
            raise self.SignerError(
                f'txHash {tx_hash}: Bridge is not linked with chainId {deposit_event["targetChainId"]}'
            )

        # check backlink from targetChainId
        target_api = self.construct_http_api(random.choice(self.config.rpc_urls[deposit_event['targetChainId']]))
        source_bridge = self.get_bridge_contract(
            target_api, target_bridge_address, poll_latency=self.config.poll_latency
        )
        backlink_address = source_bridge.call_method('links', (self.chain_id,))
        if backlink_address != self.bridge.contract.address:
            raise self.SignerError(f'txHash {tx_hash}: Bridge for chainId {deposit_event["targetChainId"]} '
                                   f'not linked with target bridge')
        util.eth_add_to_auto_sign(target_api, self.account)
        source_bridge.execute_tx(
            'list', ([
                         [
                             int(target_asset, 16), int(deposit_event['receiver'], 16),
                             deposit_event['amount'], self.chain_id, int(tx_hash, 16)
                         ]
                     ],),
            {'from': self.account.address}
        )

    def listen(self, from_block_number: int, to_block_number: typing.Optional[int] = None):
        events = self.bridge.contract.events.Deposit.get_logs(fromBlock=from_block_number, toBlock=to_block_number)
        for event in events:
            self.list_by_event(event)
