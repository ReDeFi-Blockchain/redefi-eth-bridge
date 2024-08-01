import random
import time
import typing

from .base import Worker

from src.models import Transfer


__all__ = ['WebScanner']


class WebScanner(Worker):
    def find_deposit_block_id(self, chain_id: int, tx_hash):
        if chain_id not in self.config.rpc_urls:
            raise ValueError(f'No route to chainId {chain_id}')
        source_api = self.construct_http_api(random.choice(self.config.rpc_urls[chain_id]))
        source_tx = source_api.eth.get_transaction(tx_hash)
        if source_tx is None:
            raise ValueError(f'No transaction with txHash {tx_hash}')
        return source_tx['blockNumber']

    def listen_listed(self, from_block_number: int, to_block_number: typing.Optional[int] = None):
        events = self.bridge.contract.events.Listed.get_logs(fromBlock=from_block_number, toBlock=to_block_number)
        for event in events:
            listed_event = event['args']
            transfer = Transfer.get_or_create(listed_event['txHash'].hex())
            transfer.sender_chain_id = listed_event['sourceChainId']
            transfer.listed_event_block_id = event['blockNumber']
            try:
                transfer.deposit_event_block_id = self.find_deposit_block_id(
                    transfer.sender_chain_id, listed_event['txHash']
                )
            except Exception as e:
                self.log.warning(
                    f'Unable to get deposit event for '
                    f'chainId={transfer.sender_chain_id} and txHash={transfer.tx_hash}: {str(e)}'
                )
            transfer.save()

    def listen_confirmations(self, from_block_number: int, to_block_number: typing.Optional[int] = None):
        events = self.bridge.contract.events.Confirmed.get_logs(fromBlock=from_block_number, toBlock=to_block_number)
        for event in events:
            confirmed_event = event['args']
            transfer = Transfer.get_or_create(confirmed_event['txHash'].hex())
            transfer.validator_confirmations = len(self.bridge.call_method('confirmedBy', (confirmed_event['txHash'],)))
            transfer.save()

    def listen_blocks(self, last_block: int = 0) -> int:
        current_block = self.api.eth.block_number - self.config.eth_block_confirmations
        if last_block >= current_block:
            time.sleep(self.config.poll_latency)
            return current_block
        to_block = min(last_block + 10, current_block)
        self.listen_listed(from_block_number=last_block, to_block_number=to_block)
        self.listen_confirmations(from_block_number=last_block, to_block_number=to_block)
        return to_block
