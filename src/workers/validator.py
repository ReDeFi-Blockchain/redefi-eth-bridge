import random
import typing

from web3.types import EventData

from .base import Worker, WorkerConfig
from src import util


__all__ = ['Validator']


class Validator(Worker):
    LOGGER_NAME = 'worker.validator'

    def __init__(self, config: WorkerConfig = None):
        super().__init__(config)
        self.bridge = self.get_bridge_contract(
            self.api, self.config.eth_contract_address, poll_latency=self.config.poll_latency
        )
        self.chain_id = int(self.api.eth.chain_id)

    class ValidatorException(Exception):
        def __init__(self, message: str):
            self.message = message

    class ValidatorDebug(ValidatorException):
        pass

    class ValidatorInfo(ValidatorException):
        pass

    class ValidatorError(ValidatorException):
        pass

    def validate_event(self, event: EventData):
        listed_event = event['args']
        tx_hash = listed_event['txHash'].hex()
        if listed_event['sourceChainId'] not in self.config.rpc_urls:
            raise self.ValidatorDebug(f'Unable to validate txHash {tx_hash}, '
                                      f'network with chainId {listed_event["sourceChainId"]} unreachable')

        # check link to sourceChainId
        source_bridge_address = self.bridge.call_method('links', (listed_event['sourceChainId'],))
        if source_bridge_address == util.ADDRESS_0:
            raise self.ValidatorError(f'txHash {tx_hash}: '
                                      f'Bridge is not linked with chainId {listed_event["sourceChainId"]}')

        # check backlink from sourceChainId
        source_api = self.construct_http_api(random.choice(self.config.rpc_urls[listed_event['sourceChainId']]))
        source_bridge = self.get_bridge_contract(
            source_api, source_bridge_address, poll_latency=self.config.poll_latency
        )
        backlink_address = source_bridge.call_method('links', (self.chain_id,))
        if backlink_address != self.bridge.contract.address:
            raise self.ValidatorError(f'txHash {tx_hash}: Bridge for chainId '
                                      f'{listed_event["sourceChainId"]} not linked with target bridge')

        # Get the transaction from other network and check listed
        source_tx = source_api.eth.get_transaction(tx_hash)
        _, decoded_input = source_bridge.contract.decode_function_input(source_tx['input'])
        listed_receiver, listed_amount, listed_token_id, is_sent = self.bridge.call_method(
            'confirmations', (listed_event['txHash'],)
        )

        if decoded_input['_targetChainId'] != self.chain_id:
            raise self.ValidatorError(f'txHash {tx_hash}: Source transaction from chainId '
                                      f'{listed_event["sourceChainId"]} contains wrong target chainId')

        if decoded_input['_receiver'] != listed_receiver:
            raise self.ValidatorError(f'txHash {tx_hash}: Wrong receiver on target chain')

        if decoded_input['_amount'] != listed_amount:
            raise self.ValidatorError(f'txHash {tx_hash}: Wrong amount on target chain')

        if is_sent:
            raise self.ValidatorInfo(f'txHash {tx_hash}: Tokens already sent, nothing to validate')

        # Check that registered asset matches the listed
        if not source_bridge.call_method('hasPair', (decoded_input['_token'], self.chain_id)):
            raise self.ValidatorError(f'txHash {tx_hash}: Source asset has not pair on target chain')

        # check that asset mapped correctly
        source_asset = source_bridge.call_method('getDestinationAddress', (decoded_input['_token'], self.chain_id))
        target_asset = self.bridge.call_method('tokens', (listed_token_id - 1,))
        if source_asset != target_asset:
            self.ValidatorError(f'txHash {tx_hash}: Source asset {source_asset} != {target_asset} on target chain')
        return listed_event['txHash']

    def confirm(self, tx_hash: str):
        # Confirm the transaction onchain
        self.bridge.execute_tx('confirm', ([tx_hash],), {'from': self.account.address})

    def validate(self, from_block_number: int, to_block_number: typing.Optional[int] = None):
        # We get Listed event for validators on network
        events = self.bridge.contract.events.Listed.get_logs(fromBlock=from_block_number, toBlock=to_block_number)
        for event in events:
            try:
                tx_hash = self.validate_event(event)
            except self.ValidatorError as e:
                self.log.error(e.message)
                continue
            except self.ValidatorInfo as e:
                self.log.info(e.message)
                continue
            except self.ValidatorDebug as e:
                self.log.debug(e.message)
                continue

            self.confirm(tx_hash)
