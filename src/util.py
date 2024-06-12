import typing

import web3
from web3.middleware.signing import construct_sign_and_send_raw_middleware
import eth_account.account
import solcx
from substrateinterface.utils.ss58 import ss58_encode, ss58_decode
from substrateinterface.utils.hasher import blake2_256

from src import bridge_types as types


__all__ = [
    'ContractHelper', 'EthBalanceChecker', 'ContractWrapper',
    'evm_to_address', 'address_to_evm', 'eth_add_to_auto_sign',
    'ADDRESS_0'
]

ADDRESS_0 = '0x0000000000000000000000000000000000000000'


class ContractHelper(object):
    @classmethod
    def compile(
        cls, code: str, solc_version='0.8.22', contract_name: str = None
    ) -> typing.TypedDict('ContractInterface', {'abi': list, 'bin': bytes}):
        compiled_sol = solcx.compile_source(code, solc_version=solc_version, output_values=['abi', 'bin'])

        contract_id, contract_interface = (
            compiled_sol.popitem() if contract_name is None
            else (f'<stdin>:{contract_name}', compiled_sol[f'<stdin>:{contract_name}'])
        )
        return contract_interface

    @classmethod
    def deploy_by_code(
        cls, api: web3.Web3, deployer: eth_account.account.LocalAccount, constructor_args: tuple = (),
        code: str = None, solc_version: str = '0.8.22', contract_name: str = None
    ) -> typing.TypedDict('Contract', {'abi': list, 'address': types.Address}):
        contract_interface = cls.compile(code, solc_version=solc_version, contract_name=contract_name)

        contract = api.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
        tx_hash = contract.constructor(*constructor_args).transact({'from': deployer.address})
        tx_receipt = api.eth.wait_for_transaction_receipt(tx_hash)

        return {'address': tx_receipt.contractAddress, 'abi': contract_interface['abi']}

    @classmethod
    def deploy_by_bytecode(
        cls, api: web3.Web3, deployer: eth_account.account.LocalAccount, constructor_args: tuple = (),
        abi: list = None, bytecode: bytes = None
    ):
        contract = api.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = contract.constructor(*constructor_args).transact({'from': deployer.address})
        tx_receipt = api.eth.wait_for_transaction_receipt(tx_hash)

        return {'address': tx_receipt.contractAddress, 'abi': abi}


def evm_to_address(evm_address: str, ss58_prefix=42) -> str:
    message = b'evm:' + bytes.fromhex(evm_address[2 if evm_address.startswith("0x") else 0:])
    address_bytes = blake2_256(message)
    return ss58_encode(address_bytes, ss58_prefix)


def address_to_evm(address: str) -> str:
    return '0x' + ss58_decode(address)[:40]


class EthBalanceChecker(object):
    def __init__(self, api: web3.Web3, address: types.Address):
        self.api = api
        self.address = address
        self.balance = {
            'before': 0,
            'after': 0,
            'delta': 0
        }

    def __enter__(self):
        self.balance['before'] = self.api.eth.get_balance(self.address)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.balance['after'] = self.api.eth.get_balance(self.address)
        self.balance['delta'] = self.balance['after'] - self.balance['before']


class ContractWrapper(object):
    def __init__(self, api: web3.Web3, contract_address: types.Address, contract_abi: list, poll_latency: float = 1.0):
        self.api = api
        self._contract_address = contract_address
        self.contract = self.api.eth.contract(contract_address, abi=contract_abi)
        self.poll_latency = poll_latency

    @property
    def address(self):
        return self._contract_address

    def call_method(self, method_name: str, arguments: tuple = ()):
        return getattr(self.contract.functions, method_name)(*arguments).call()

    def make_tx(self, method_name: str, arguments: tuple = ()):
        return getattr(self.contract.functions, method_name)(*arguments)

    def execute_tx(self, method_name: str, arguments: tuple = (), options: dict = None):
        tx_hash = self.make_tx(method_name, arguments).transact(options)
        return self.api.eth.wait_for_transaction_receipt(tx_hash, poll_latency=self.poll_latency)


def eth_add_to_auto_sign(api: web3.Web3, account: eth_account.account.LocalAccount):
    api.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
