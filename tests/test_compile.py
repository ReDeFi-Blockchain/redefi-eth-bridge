import os

import solcx

from tests.base import EthTestCase
from src.util import EthBalanceChecker, ContractHelper, ContractWrapper

CONTRACTS_DIR = os.path.join('..', 'contracts')


class CompileTestCase(EthTestCase):
    SOLC_VERSION = '0.8.24'
    DEPLOYER_BALANCE = 30

    @classmethod
    def setUpClass(cls):
        solcx.install_solc(cls.SOLC_VERSION)

    def test_base_compile(self):
        api, deployer = self.get_api_and_deployer()

        with EthBalanceChecker(api, deployer.address) as checker:
            self.transfer_balance(deployer.address, self.DEPLOYER_BALANCE)

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
        api, deployer = self.get_api_and_deployer()

        with EthBalanceChecker(api, deployer.address) as checker:
            self.transfer_balance(deployer.address, self.DEPLOYER_BALANCE)

        print('balance', checker.balance)

        with EthBalanceChecker(api, deployer.address) as checker:
            with open(os.path.join(CONTRACTS_DIR, 'BridgeLinked.sol'), 'r', encoding='utf-8') as f:
                contract_data = ContractHelper.deploy_by_code(
                    api, deployer,
                    code=f.read(), constructor_args=(deployer.address,), solc_version=self.SOLC_VERSION,
                    contract_name='Bridge'
                )

        print('balance', checker.balance)

        contract = ContractWrapper(api, contract_data['address'], contract_data['abi'])

        self.assertEqual(contract.call_method('admin'), deployer.address)
        self.assertEqual(contract.call_method('owner'), deployer.address)
