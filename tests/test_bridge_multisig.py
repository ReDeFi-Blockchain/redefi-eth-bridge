import unittest

from tests.config import Config
from tests.util import get_cache, get_eth_api_and_account, eth_add_to_auto_sign, transfer_balance_substrate
from src.util import ContractHelper, ContractWrapper


ONE_TOKEN = 10 ** 18


class BridgeTestCase(unittest.TestCase):
    SOLC_VERSION = '0.8.24'

    TARGET_ETH = 1
    TARGET_RELAY = 47803

    def test_bridge_multi_sig_base(self):
        api, deployer = get_eth_api_and_account(Config.FRONTIER_RPC)
        users = {'user2': api.eth.account.create()}
        for user_key in ('signer', 'validator1', 'validator2', 'validator3', 'user1'):
            users[user_key] = api.eth.account.create()
            eth_add_to_auto_sign(api, users[user_key])
        for user, amount in (
            (deployer, 100),
            (users['signer'], 100),
            *((users[x], 10) for x in ('validator1', 'validator2', 'validator3', 'user1', 'user2'))
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
            abi=cached['bridge_multi_sig']['abi'], bytecode=cached['bridge_multi_sig']['bin']
        )
        bridge = ContractWrapper(api, deployed['address'], deployed['abi'])

        # Add signer account for money transfers
        bridge.execute_tx(
            'setSigner', (users['signer'].address,),
            {'from': deployer.address}
        )

        # Add validator accounts
        bridge.execute_tx(
            'addValidators',
            ([users['validator1'].address, users['validator2'].address, users['validator3'].address,],),
            {'from': deployer.address}
        )

        # Set required confirmations
        self.assertEqual(bridge.call_method('requiredConfirmations'), 0)
        bridge.execute_tx(
            'setRequiredConfirmations', (2,),
            {'from': deployer.address}
        )
        self.assertEqual(bridge.call_method('requiredConfirmations'), 2)

        # Add tokens to bridge trusted list
        bridge.execute_tx(
            'addTokens', ([ethereum_bax.contract.address, relay_bax.contract.address],),
            {'from': deployer.address}
        )

        # Check tokens list
        ETHEREUM_BAX_ID = 1
        RELAY_BAX_ID = 2
        self.assertEqual(bridge.call_method('isToken', (ethereum_bax.contract.address,)), [ETHEREUM_BAX_ID, False])
        self.assertEqual(bridge.call_method('isToken', (relay_bax.contract.address,)), [RELAY_BAX_ID, False])

        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (deployer.address,)),
            1_000 * ONE_TOKEN
        )
        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (users['user1'].address,)),
            0
        )
        # seems strange to approve account itself, but this implementation require it
        ethereum_bax.execute_tx(
            'approve', (deployer.address, 1_000 * ONE_TOKEN),
            {'from': deployer.address}
        )
        ethereum_bax.execute_tx(
            'transferFrom', (deployer.address, users['user1'].address, 10 * ONE_TOKEN),
            {'from': deployer.address}
        )
        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (deployer.address,)),
            990 * ONE_TOKEN
        )
        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (users['user1'].address,)),
            10 * ONE_TOKEN
        )
        ethereum_bax.execute_tx(
            'approve', (bridge.contract.address, 10 * ONE_TOKEN),
            {'from': users['user1'].address}
        )
        self.assertEqual(
            ethereum_bax.call_method('balanceOf', (bridge.contract.address,)),
            0
        )

        # User1 send 10 tokens to eth bridge for user2 on relay
        result = bridge.execute_tx(
            'deposit', (users['user2'].address, ethereum_bax.contract.address, 10 * ONE_TOKEN, self.TARGET_RELAY),
            {'from': users['user1'].address}
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
                'amount': 10 * ONE_TOKEN, 'receiver': users['user2'].address,
                'token': ethereum_bax.contract.address, 'targetChainId': self.TARGET_RELAY
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

        # Now signer must place new txHash for validators approval
        bridge.execute_tx(
            'list', ([
                [
                    int(relay_bax.contract.address, 16), int(users['user2'].address, 16),
                    10 * ONE_TOKEN, int(result['transactionHash'].hex(), 16)
                ]
            ],),
            {'from': users['signer'].address}
        )

        # Validators (Only 2 of 3) approve transaction
        for user_key in ('validator1', 'validator2'):
            bridge.execute_tx(
                'confirm', ([result['transactionHash']],),
                {'from': users[user_key].address}
            )

        # Validator can not approve transaction twice
        with self.assertRaises(ValueError) as e:
            bridge.execute_tx(
                'confirm', ([result['transactionHash']],),
                {'from': users[user_key].address}
            )
        self.assertTrue('bridge: txHash already confirmed' in str(e.exception))

        # Validator can not approve transaction before signer list it
        with self.assertRaises(ValueError) as e:
            bridge.execute_tx(
                'confirm', (['0x' + ''.join(reversed(result['transactionHash'].hex()[2:]))],),
                {'from': users[user_key].address}
            )
        self.assertTrue('bridge: unknown txHash' in str(e.exception))

        # Bridge worker execute transfer transaction from its signer
        self.assertEqual(
            relay_bax.call_method('balanceOf', (users['user2'].address,)),
            0
        )
        bridge.execute_tx(
            'transfer', ([result['transactionHash'].hex()],),
            {'from': users['signer'].address}
        )
        self.assertEqual(
            relay_bax.call_method('balanceOf', (users['user2'].address,)),
            10 * ONE_TOKEN
        )
        self.assertEqual(
            relay_bax.call_method('balanceOf', (bridge.contract.address,)),
            90 * ONE_TOKEN
        )
        # Ensure that txHash of transfer registered in contract state
        self.assertEqual(
            bridge.call_method('confirmations', (result['transactionHash'],)),
            # receiver, amount, tokenId, isSent
            [users['user2'].address, 10 * ONE_TOKEN, RELAY_BAX_ID, True]
        )
        # Bridge must skip transfer if already execute it (Check by txHash)
        bridge.execute_tx(
            'transfer', ([result['transactionHash'].hex()],),
            {'from': users['signer'].address}
        )
        # Balances not changed since last run
        self.assertEqual(
            relay_bax.call_method('balanceOf', (users['user2'].address,)),
            10 * ONE_TOKEN
        )
        self.assertEqual(
            relay_bax.call_method('balanceOf', (bridge.contract.address,)),
            90 * ONE_TOKEN
        )
