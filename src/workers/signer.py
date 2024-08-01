import time
import typing
import random

from .base import Worker
from src import util


__all__ = ['Signer']


class Signer(Worker):
    TYPE_LISTER = 'lister'
    TYPE_TRANSACTOR = 'transactor'

    class SignerException(Exception):
        def __init__(self, message: str):
            self.message = message

    class SignerError(SignerException):
        pass

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
        listed_receiver, listed_amount, listed_token_id, is_sent = source_bridge.call_method(
            'confirmations', (tx_hash,)
        )
        if listed_amount > 0:
            raise self.SignerError(f'txHash {tx_hash}: txHash already listed')
        backlink_address = source_bridge.call_method('links', (self.chain_id,))
        if backlink_address != self.bridge.contract.address:
            raise self.SignerError(f'txHash {tx_hash}: Bridge for chainId {deposit_event["targetChainId"]} '
                                   f'not linked with target bridge')
        util.eth_add_to_auto_sign(target_api, self.account)
        tx = source_bridge.execute_tx(
            'list', ([
                         [
                             int(target_asset, 16), int(deposit_event['receiver'], 16),
                             deposit_event['amount'], self.chain_id, int(tx_hash, 16)
                         ]
                     ],),
            {'from': self.account.address}
        )
        self.log.info(f'[worker.{self.__class__.__name__.lower()}.{self.name}] '
                      f'listed txHash {tx_hash} in block #{tx["blockNumber"]}')
        return tx

    def listen_deposits(self, from_block_number: int, to_block_number: typing.Optional[int] = None):
        events = self.bridge.contract.events.Deposit.get_logs(fromBlock=from_block_number, toBlock=to_block_number)
        block_numbers = []
        if events:
            self.log.info(f'[worker.{self.__class__.__name__.lower()}.{self.name}] '
                          f'Got ({len(events)}) deposit events from users '
                          f'in blocks #{from_block_number}-#{to_block_number}')
        for event in events:
            block_numbers.append(self.list_by_event(event)['blockNumber'])

        return block_numbers

    def transfer(self, tx_hash):
        return self.bridge.execute_tx('transfer', ([tx_hash],), {'from': self.account.address})

    def confirm_by_event(self, event, required_confirmations=None):
        required_confirmations = (
            self.bridge.call_method('requiredConfirmations')
            if required_confirmations is None else required_confirmations
        )
        tx_hash = event['args']['txHash']
        current_confirmations = self.bridge.call_method('confirmedBy', (tx_hash,))
        if len(current_confirmations) < required_confirmations:
            return
        _, _, _, is_sent = self.bridge.call_method('confirmations', (tx_hash,))
        if is_sent:
            return
        tx = self.transfer(tx_hash)
        self.log.info(f'[worker.{self.__class__.__name__.lower()}.{self.name}] '
                      f'confirm (call transfer) txHash {tx_hash} in block #{tx["blockNumber"]}')

    def listen_confirmations(self, from_block_number: int, to_block_number: typing.Optional[int] = None):
        events = self.bridge.contract.events.Confirmed.get_logs(fromBlock=from_block_number, toBlock=to_block_number)
        if not events:
            return
        self.log.info(f'[worker.{self.__class__.__name__.lower()}.{self.name}] '
                      f'Got ({len(events)}) confirmation events from validators '
                      f'in blocks #{from_block_number}-#{to_block_number}')
        required_confirmations = self.bridge.call_method('requiredConfirmations')
        for event in events:
            self.confirm_by_event(event, required_confirmations)

    def listen_blocks(self, last_block: int = 0) -> int:
        current_block = self.api.eth.block_number - self.config.eth_block_confirmations
        while last_block >= current_block:
            time.sleep(self.config.poll_latency)
            current_block = self.api.eth.block_number - self.config.eth_block_confirmations
        
        to_block = min(last_block + 10, current_block)

        if self.name == self.TYPE_LISTER:
            self.listen_deposits(from_block_number=last_block, to_block_number=to_block)
        if self.name == self.TYPE_TRANSACTOR:
            self.listen_confirmations(from_block_number=last_block, to_block_number=to_block)

        return to_block

    def listen(self):
        if self.name not in (self.TYPE_LISTER, self.TYPE_TRANSACTOR):
            raise ValueError(f'Signer name must be one of [{self.TYPE_LISTER}, {self.TYPE_TRANSACTOR}]')
        super().listen()
