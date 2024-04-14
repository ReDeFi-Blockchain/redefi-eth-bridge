import os
import unittest

import solcx

from tests.config import Config
from tests.util import transfer_balance_substrate, get_eth_api_and_account
from src.util import EthBalanceChecker, ContractHelper, ContractWrapper

CONTRACTS_DIR = os.path.join('..', 'contracts')


class CompileTestCase(unittest.TestCase):
    SOLC_VERSION = '0.8.24'
    DEPLOYER_BALANCE = 30

    @classmethod
    def setUpClass(cls):
        solcx.install_solc(cls.SOLC_VERSION)

    def test_base_compile(self):
        api, deployer = get_eth_api_and_account(Config.FRONTIER_RPC)

        with EthBalanceChecker(api, deployer.address) as checker:
            transfer_balance_substrate(
                Config.SUBSTRATE_WS, Config.SUBSTRATE_DONOR,
                receiver={'ethereum': deployer.address}, tokens=self.DEPLOYER_BALANCE
            )
        print('balance', checker.balance)

        with EthBalanceChecker(api, deployer.address) as checker:
            with open(os.path.join('.', 'data', 'SimpleContract.sol'), 'r', encoding='utf-8') as f:
                contract_data = ContractHelper.deploy_by_code(
                    api, deployer,
                    code=f.read(), constructor_args=('first',), solc_version=self.SOLC_VERSION
                )

        print('balance', checker.balance)

        contract = ContractWrapper(api, contract_data['address'], contract_data['abi'])

        message = contract.call_method('message')

        self.assertEqual(message, 'first')

        contract.execute_tx('writeBillboard', ('second', ), {'from': deployer.address})

        message = contract.call_method('message')

        self.assertEqual(message, 'second')

    def test_compile_bridge(self):
        api, deployer = get_eth_api_and_account(Config.FRONTIER_RPC)

        with EthBalanceChecker(api, deployer.address) as checker:
            transfer_balance_substrate(
                Config.SUBSTRATE_WS, Config.SUBSTRATE_DONOR,
                receiver={'ethereum': deployer.address}, tokens=self.DEPLOYER_BALANCE
            )
        print('balance', checker.balance)

        with EthBalanceChecker(api, deployer.address) as checker:
            with open(os.path.join(CONTRACTS_DIR, 'Bridge.sol'), 'r', encoding='utf-8') as f:
                contract_data = ContractHelper.deploy_by_code(
                    api, deployer,
                    code=f.read(), constructor_args=(deployer.address,), solc_version=self.SOLC_VERSION,
                    contract_name='Bridge'
                )

        print('balance', checker.balance)

        contract = ContractWrapper(api, contract_data['address'], contract_data['abi'])

        self.assertEqual(contract.call_method('admin'), deployer.address)
        self.assertEqual(contract.call_method('owner'), deployer.address)
