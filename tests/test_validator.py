import unittest

from tests.config import Config
from tests.util import (
    get_contract_cache, get_eth_api_and_account, eth_add_to_auto_sign, transfer_balance_substrate, write_cache
)
from src.util import ContractHelper, ContractWrapper
from src.workers import Validator, WorkerConfig, Signer


ONE_TOKEN = 10 ** 18


class BridgeTestCase(unittest.TestCase):
    SOLC_VERSION = '0.8.24'

    def init_bridge(self, api, deployer, code, signer_address, validator_address, bax_address):
        deployed = ContractHelper.deploy_by_bytecode(
            api, deployer, (deployer.address,),
            abi=code['abi'], bytecode=code['bin']
        )
        bridge = ContractWrapper(api, deployed['address'], deployed['abi'])

        # Add signer account for money transfers
        bridge.execute_tx(
            'setSigner', (signer_address,),
            {'from': deployer.address}
        )

        # Add validator accounts
        bridge.execute_tx(
            'addValidators',
            ([validator_address],),
            {'from': deployer.address}
        )

        # Set required confirmations
        self.assertEqual(bridge.call_method('requiredConfirmations'), 0)
        bridge.execute_tx(
            'setRequiredConfirmations', (1,),
            {'from': deployer.address}
        )
        self.assertEqual(bridge.call_method('requiredConfirmations'), 1)

        # Add tokens to bridge trusted list
        bridge.execute_tx(
            'addTokens', ([bax_address],),
            {'from': deployer.address}
        )

        return bridge

    def test_bridge_linked_validator(self):
        api_relay, _deployer = get_eth_api_and_account(Config.FRONTIER_RPC)
        api_eth, _deployer_eth = get_eth_api_and_account(Config.SECOND_FRONTIER_RPC)
        target_eth = int(api_eth.eth.chain_id)
        target_relay = int(api_relay.eth.chain_id)
        rpc_urls_path = write_cache(
            'rpc_urls.json', {target_eth: [Config.SECOND_FRONTIER_RPC], target_relay: [Config.FRONTIER_RPC]}
        )
        users = {'user2': api_relay.eth.account.create(), 'deployer_eth': _deployer_eth, 'deployer_relay': _deployer}
        for user_key in ('signer_eth', 'validator_eth', 'user1'):
            users[user_key] = api_eth.eth.account.create()
            eth_add_to_auto_sign(api_eth, users[user_key])
        for user_key in ('signer_relay', 'validator_relay'):
            users[user_key] = api_relay.eth.account.create()
            eth_add_to_auto_sign(api_relay, users[user_key])
        for user, amount in (
            *((users[x], 100) for x in ('deployer_relay', 'signer_relay')),
            *((users[x], 10) for x in ('validator_relay',))
        ):
            transfer_balance_substrate(
                Config.SUBSTRATE_WS, '//Alice', {'ethereum': user.address}, amount
            )
        for user, amount in (
            *((users[x], 100) for x in ('deployer_eth', 'signer_eth',)),
            *((users[x], 10) for x in ('validator_eth', 'user1'))
        ):
            transfer_balance_substrate(
                Config.SECOND_SUBSTRATE_WS, '//Alice', {'ethereum': user.address}, amount
            )
        cached = get_contract_cache(self.SOLC_VERSION)
        deployed = ContractHelper.deploy_by_bytecode(
            api_eth, users['deployer_eth'], ('Eth BAX', 'EBAX', 18, users['deployer_eth'].address, 1_000),
            abi=cached['erc20']['abi'], bytecode=cached['erc20']['bin']
        )
        bax_eth = ContractWrapper(api_eth, deployed['address'], deployed['abi'])

        deployed = ContractHelper.deploy_by_bytecode(
            api_relay, users['deployer_relay'], ('Relay BAX', 'RBAX', 18, users['deployer_relay'].address, 1_000),
            abi=cached['erc20']['abi'], bytecode=cached['erc20']['bin']
        )
        bax_relay = ContractWrapper(api_relay, deployed['address'], deployed['abi'])

        bridge_eth = self.init_bridge(
            api_eth, users['deployer_eth'], cached['bridge_linked'],
            users['signer_eth'].address, users['validator_eth'].address, bax_eth.contract.address
        )

        bridge_relay = self.init_bridge(
            api_relay, users['deployer_relay'], cached['bridge_linked'],
            users['signer_relay'].address, users['validator_relay'].address, bax_relay.contract.address
        )

        # set links on bridges on other side
        bridge_eth.execute_tx(
            'addLink', (target_relay, bridge_relay.contract.address,),
            {'from': users['deployer_eth'].address}
        )
        bridge_relay.execute_tx(
            'addLink', (target_eth, bridge_eth.contract.address,),
            {'from': users['deployer_relay'].address}
        )

        # set pair on ethereum side (For example we transfer only from eth to relay)
        bridge_eth.execute_tx(
            'addPair', (bax_eth.contract.address, target_relay, bax_relay.contract.address),
            {'from': users['deployer_eth'].address}
        )

        # seems strange to approve account itself, but this implementation require it
        bax_eth.execute_tx(
            'approve', (users['deployer_eth'].address, 1_000 * ONE_TOKEN),
            {'from': users['deployer_eth'].address}
        )
        bax_eth.execute_tx(
            'transferFrom', (users['deployer_eth'].address, users['user1'].address, 10 * ONE_TOKEN),
            {'from': users['deployer_eth'].address}
        )
        self.assertEqual(
            bax_eth.call_method('balanceOf', (users['deployer_eth'].address,)),
            990 * ONE_TOKEN
        )
        self.assertEqual(
            bax_eth.call_method('balanceOf', (users['user1'].address,)),
            10 * ONE_TOKEN
        )
        bax_eth.execute_tx(
            'approve', (bridge_eth.contract.address, 10 * ONE_TOKEN),
            {'from': users['user1'].address}
        )
        self.assertEqual(
            bax_eth.call_method('balanceOf', (bridge_eth.contract.address,)),
            0
        )

        # User1 send 10 tokens to eth bridge for user2 on relay
        result = bridge_eth.execute_tx(
            'deposit', (users['user2'].address, bax_eth.contract.address, 10 * ONE_TOKEN, target_relay),
            {'from': users['user1'].address}
        )
        self.assertEqual(
            bax_eth.call_method('balanceOf', (bridge_eth.contract.address,)),
            10 * ONE_TOKEN
        )

        # At first we need to give contract balance in other token to transfer
        self.assertEqual(
            bax_relay.call_method('balanceOf', (bridge_relay.contract.address,)),
            0
        )
        bax_relay.execute_tx(
            'approve', (users['deployer_relay'].address, 1000 * ONE_TOKEN),
            {'from': users['deployer_relay'].address}
        )
        bax_relay.execute_tx(
            'transferFrom', (users['deployer_relay'].address, bridge_relay.contract.address, 100 * ONE_TOKEN),
            {'from': users['deployer_relay'].address}
        )
        self.assertEqual(
            bax_relay.call_method('balanceOf', (bridge_relay.contract.address,)),
            100 * ONE_TOKEN
        )  # Now contract has 100 RBAX

        # Now bridge worker must scan events from chain. We already have blockNumber of event, so scan only this block
        signer_config = WorkerConfig()
        signer_config.eth_private_key = users['signer_relay'].key
        signer_config.eth_contract_address = bridge_eth.contract.address
        signer_config.eth_rpc = Config.SECOND_FRONTIER_RPC
        signer_config.rpc_urls_file_path = rpc_urls_path

        signer = Signer(signer_config)

        signer.listen(from_block_number=result['blockNumber'])

        # Validator check transaction
        validator_config = WorkerConfig()
        validator_config.eth_private_key = users['validator_relay'].key
        validator_config.eth_contract_address = bridge_relay.contract.address
        validator_config.eth_rpc = Config.FRONTIER_RPC
        validator_config.rpc_urls_file_path = rpc_urls_path

        validator = Validator(validator_config)

        validator.validate(from_block_number=result['blockNumber'])

        # Bridge worker execute transfer transaction from its signer
        self.assertEqual(
            bax_relay.call_method('balanceOf', (users['user2'].address,)),
            0
        )
        bridge_relay.execute_tx(
            'transfer', ([result['transactionHash'].hex()],),
            {'from': users['signer_relay'].address}
        )
        self.assertEqual(
            bax_relay.call_method('balanceOf', (users['user2'].address,)),
            10 * ONE_TOKEN
        )
        self.assertEqual(
            bax_relay.call_method('balanceOf', (bridge_relay.contract.address,)),
            90 * ONE_TOKEN
        )
        # Ensure that txHash of transfer registered in contract state
        listed_token_id = 1
        self.assertEqual(
            bridge_relay.call_method('confirmations', (result['transactionHash'],)),
            # receiver, amount, tokenId, isSent
            [users['user2'].address, 10 * ONE_TOKEN, listed_token_id, True]
        )
