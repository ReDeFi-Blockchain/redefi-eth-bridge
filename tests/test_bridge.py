import unittest

from tests.config import Config
from tests.util import get_cache, get_eth_api_and_account, eth_add_to_auto_sign, transfer_balance_substrate
from src.util import ContractHelper, ContractWrapper


ONE_TOKEN = 10 ** 18


class BridgeTestCase(unittest.TestCase):
    SOLC_VERSION = '0.8.24'

    TARGET_ETH = 1
    TARGET_RELAY = 47803

    def test_bridge_base(self):
        api, deployer = get_eth_api_and_account(Config.FRONTIER_RPC)
        user1 = api.eth.account.create()
        eth_add_to_auto_sign(api, user1)
        user2 = api.eth.account.create()
        for user, amount in (
            (deployer, 100),
            (user1, 10),
            (user2, 10),
        ):
            transfer_balance_substrate(
                Config.SUBSTRATE_WS, '//Alice', {'ethereum': user.address}, amount
            )
        cached = get_cache(self.SOLC_VERSION)
        deployed = ContractHelper.deploy_by_bytecode(
            api, deployer, ('Eth BAX', 'EBAX', 18, deployer.address, 1_000),
            abi=cached['erc20']['abi'], bytecode=cached['erc20']['bin']
        )
        ethereum_bax = ContractWrapper(api, deployed['address'], deployed['abi'])

        deployed = ContractHelper.deploy_by_bytecode(
            api, deployer, ('Relay BAX', 'RBAX', 18, deployer.address, 1_000),
            abi=cached['erc20']['abi'], bytecode=cached['erc20']['bin']
        )
        relay_bax = ContractWrapper(api, deployed['address'], deployed['abi'])

        deployed = ContractHelper.deploy_by_bytecode(
            api, deployer, (deployer.address,),
            abi=cached['bridge']['abi'], bytecode=cached['bridge']['bin']
        )
        bridge = ContractWrapper(api, deployed['address'], deployed['abi'])

        # Add tokens to bridge trusted list
        bridge.execute_tx(
            'addTokens', ([ethereum_bax.contract.address, relay_bax.contract.address],),
            {'from': deployer.address}
        )

        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (deployer.address,)),
            1_000 * ONE_TOKEN
        )
        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (user1.address,)),
            0
        )
        # seems strange to approve account itself, but this implementation require it
        ethereum_bax.execute_tx(
            'approve', (deployer.address, 1_000 * ONE_TOKEN),
            {'from': deployer.address}
        )
        ethereum_bax.execute_tx(
            'transferFrom', (deployer.address, user1.address, 10 * ONE_TOKEN),
            {'from': deployer.address}
        )
        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (deployer.address,)),
            990 * ONE_TOKEN
        )
        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (user1.address,)),
            10 * ONE_TOKEN
        )
        ethereum_bax.execute_tx(
            'approve', (bridge.contract.address, 10 * ONE_TOKEN),
            {'from': user1.address}
        )
        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (bridge.contract.address,)),
            0
        )

        # User1 send 10 tokens to eth bridge for user2 on relay
        result = bridge.execute_tx(
            'deposit', (user2.address, ethereum_bax.contract.address, 10 * ONE_TOKEN, self.TARGET_RELAY),
            {'from': user1.address}
        )
        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (bridge.contract.address,)),
            10 * ONE_TOKEN
        )

        # Now bridge worker must scan events from chain. We already have blockNumber of event, so scan only this block
        events = bridge.contract.events.Deposit.get_logs(fromBlock=result['blockNumber'])
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0]['args'],
            {
                'amount': 10 * ONE_TOKEN, 'from': user2.address,
                'token': ethereum_bax.contract.address, 'targetChain': self.TARGET_RELAY
            }
        )
        # important, we use transactionHash as identifier of transfer on other side
        self.assertEqual(events[0]['transactionHash'], result['transactionHash'])

        # Worker maps tokens from other network itself, not by contract.
        # So, we map ethereum_bax to relay_bax and transfer them to user2
        # But first we need to give contract balance in other token to transfer
        self.assertEqual(
            relay_bax.call_method('balanceOf', (bridge.contract.address,)),
            0
        )
        relay_bax.execute_tx(
            'approve', (deployer.address, 1000 * ONE_TOKEN),
            {'from': deployer.address}
        )
        relay_bax.execute_tx(
            'transferFrom', (deployer.address, bridge.contract.address, 100 * ONE_TOKEN),
            {'from': deployer.address}
        )
        self.assertEqual(
            relay_bax.call_method('balanceOf', (bridge.contract.address,)),
            100 * ONE_TOKEN
        )  # Now contract has 100 RBAX

        # Bridge worker execute transfer transaction from its admin
        self.assertEqual(
            relay_bax.call_method('balanceOf', (user2.address,)),
            0
        )
        bridge.execute_tx(
            'transfer', ([
                [
                    int(relay_bax.contract.address, 16), int(user2.address, 16),
                    10 * ONE_TOKEN, int(result['transactionHash'].hex(), 16)
                ]
            ],),
            {'from': deployer.address}
        )
        self.assertEqual(
            relay_bax.call_method('balanceOf', (user2.address,)),
            10 * ONE_TOKEN
        )
        self.assertEqual(
            relay_bax.call_method('balanceOf', (bridge.contract.address,)),
            90 * ONE_TOKEN
        )
        # Ensure that txHash of transfer registered in contract state
        self.assertEqual(
            bridge.call_method('exists', (result['transactionHash'],)),
            True
        )
        # Bridge must skip transfer if already execute it (Check by txHash)
        bridge.execute_tx(
            'transfer', ([
                [
                    int(relay_bax.contract.address, 16), int(user2.address, 16),
                    10 * ONE_TOKEN, int(result['transactionHash'].hex(), 16)
                ]
            ],),
            {'from': deployer.address}
        )
        # Balances not changed since last run
        self.assertEqual(
            relay_bax.call_method('balanceOf', (user2.address,)),
            10 * ONE_TOKEN
        )
        self.assertEqual(
            relay_bax.call_method('balanceOf', (bridge.contract.address,)),
            90 * ONE_TOKEN
        )
