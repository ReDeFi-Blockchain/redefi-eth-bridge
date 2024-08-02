from tests.base import EthTestCase
from tests.util import get_contract_cache, eth_add_to_auto_sign
from src.util import ContractHelper, ContractWrapper


ONE_TOKEN = 10 ** 18


class BridgeTestCase(EthTestCase):
    SOLC_VERSION = '0.8.24'

    TARGET_ETH = 1
    TARGET_RELAY = 47803

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
            'registerTokens', ([bax_address],),
            {'from': deployer.address}
        )

        return bridge

    def test_bridge_linked_base(self):
        api, _deployer = self.get_api_and_deployer()
        users = {'user2': api.eth.account.create(), 'deployer_eth': _deployer}
        for user_key in ('signer_eth', 'signer_relay', 'validator_eth', 'validator_relay', 'user1', 'deployer_relay'):
            users[user_key] = api.eth.account.create()
            eth_add_to_auto_sign(api, users[user_key])
        for user, amount in (
            *((users[x], 100) for x in ('deployer_eth', 'deployer_relay', 'signer_eth', 'signer_relay')),
            *((users[x], 10) for x in ('validator_eth', 'validator_relay', 'user1', 'user2'))
        ):
            self.transfer_balance(user.address, amount)

        cached = get_contract_cache(self.SOLC_VERSION)
        deployed = ContractHelper.deploy_by_bytecode(
            api, users['deployer_eth'], ('Eth BAX', 'EBAX', 18, users['deployer_eth'].address, 1_000),
            abi=cached['erc20']['abi'], bytecode=cached['erc20']['bin']
        )
        bax_eth = ContractWrapper(api, deployed['address'], deployed['abi'])

        deployed = ContractHelper.deploy_by_bytecode(
            api, users['deployer_relay'], ('Relay BAX', 'RBAX', 18, users['deployer_relay'].address, 1_000),
            abi=cached['erc20']['abi'], bytecode=cached['erc20']['bin']
        )
        bax_relay = ContractWrapper(api, deployed['address'], deployed['abi'])

        bridge_eth = self.init_bridge(
            api, users['deployer_eth'], cached['bridge_linked'],
            users['signer_eth'].address, users['validator_eth'].address, bax_eth.contract.address
        )

        bridge_relay = self.init_bridge(
            api, users['deployer_relay'], cached['bridge_linked'],
            users['signer_relay'].address, users['validator_relay'].address, bax_relay.contract.address
        )

        # set links on bridges on other side
        bridge_eth.execute_tx(
            'addLink', (self.TARGET_RELAY, bridge_relay.contract.address,),
            {'from': users['deployer_eth'].address}
        )
        bridge_relay.execute_tx(
            'addLink', (self.TARGET_ETH, bridge_eth.contract.address,),
            {'from': users['deployer_relay'].address}
        )

        # set pair on ethereum side (For example we transfer only from eth to relay)
        bridge_eth.execute_tx(
            'addPair', (bax_eth.contract.address, self.TARGET_RELAY, bax_relay.contract.address),
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
            'deposit', (users['user2'].address, bax_eth.contract.address, 10 * ONE_TOKEN, self.TARGET_RELAY),
            {'from': users['user1'].address}
        )
        self.assertEqual(
            bax_eth.call_method('balanceOf', (bridge_eth.contract.address,)),
            10 * ONE_TOKEN
        )

        # Now bridge worker must scan events from chain. We already have blockNumber of event, so scan only this block
        events = bridge_eth.contract.events.Deposit.get_logs(fromBlock=result['blockNumber'])
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0]['args'],
            {
                'amount': 10 * ONE_TOKEN, 'receiver': users['user2'].address,
                'token': bax_eth.contract.address, 'targetChainId': self.TARGET_RELAY
            }
        )
        # important, we use transactionHash as identifier of transfer on other side
        self.assertEqual(events[0]['transactionHash'], result['transactionHash'])

        # Worker checks the pair on other side
        self.assertEqual(bridge_eth.call_method('hasPair', (bax_eth.contract.address, self.TARGET_RELAY)), True)
        self.assertEqual(
            bridge_eth.call_method('getDestinationAddress', (bax_eth.contract.address, self.TARGET_RELAY)),
            bax_relay.contract.address
        )

        # But first we need to give contract balance in other token to transfer
        self.assertEqual(
            bax_relay.call_method('balanceOf', (bridge_relay.contract.address,)),
            0
        )
        bax_relay.execute_tx(
            'approve', (bridge_relay.contract.address, 100 * ONE_TOKEN),
            {'from': users['deployer_relay'].address}
        )
        bridge_relay.execute_tx(
            'addFunds', (bax_relay.contract.address, 100 * ONE_TOKEN),
            {'from': users['deployer_relay'].address}
        )
        self.assertEqual(
            bax_relay.call_method('balanceOf', (bridge_relay.contract.address,)),
            100 * ONE_TOKEN
        )  # Now contract has 100 RBAX

        # Now signer must place new txHash for validators approval
        bridge_relay.execute_tx(
            'list', ([
                [
                    int(bax_relay.contract.address, 16), int(users['user2'].address, 16),
                    10 * ONE_TOKEN, self.TARGET_ETH, int(result['transactionHash'].hex(), 16)
                ]
            ],),
            {'from': users['signer_relay'].address}
        )

        # We get Listed event for validators on network
        events = bridge_relay.contract.events.Listed.get_logs(fromBlock=result['blockNumber'])
        self.assertEqual(len(events), 1)
        listed_event = events[0]['args']
        self.assertEqual(listed_event, {
            'txHash': result['transactionHash'], 'sourceChainId': self.TARGET_ETH
        })

        # Validator check transaction
        # First of all validator checks the link to sourceChainId
        self.assertEqual(
            bridge_relay.call_method('links', (self.TARGET_ETH,)),
            bridge_eth.contract.address
        )
        # Validator check backlink from linked contract
        self.assertEqual(
            bridge_eth.call_method('links', (self.TARGET_RELAY,)),
            bridge_relay.contract.address
        )
        # Validator get the transaction from other network and check listed
        tx = api.eth.get_transaction(listed_event['txHash'])
        _, decoded_input = bridge_eth.contract.decode_function_input(tx['input'])
        listed_receiver, listed_amount, listed_token_id, is_sent = bridge_relay.call_method(
            'confirmations', (listed_event['txHash'],)
        )
        self.assertEqual(decoded_input['_targetChainId'], self.TARGET_RELAY)
        self.assertEqual(listed_receiver, decoded_input['_receiver'])
        self.assertEqual(listed_amount, decoded_input['_amount'])
        self.assertEqual(is_sent, False)
        # Validator must check that registered asset matches the listed
        self.assertEqual(
            bridge_eth.call_method('hasPair', (decoded_input['_token'], self.TARGET_RELAY)), True
        )
        # Validator checks that asset mapped correctly
        self.assertEqual(
            bridge_eth.call_method('getDestinationAddress', (decoded_input['_token'], self.TARGET_RELAY)),
            bridge_relay.call_method('tokens', (listed_token_id - 1,))
        )
        # Now validator can confirm transaction
        bridge_relay.execute_tx('confirm', ([listed_event['txHash']],), {'from': users['validator_relay'].address})

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
        self.assertEqual(
            bridge_relay.call_method('confirmations', (result['transactionHash'],)),
            # receiver, amount, tokenId, isSent
            [users['user2'].address, 10 * ONE_TOKEN, listed_token_id, True]
        )
