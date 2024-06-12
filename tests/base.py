import unittest

from tests.config import Config
from tests.util import get_eth_api_and_account, transfer_balance_substrate, transfer_balance_eth


__all__ = ['EthTestCase']


class EthTestCase(unittest.TestCase):
    @classmethod
    def get_first_rpc(cls):
        if Config.RUN_MODE == Config.MODE_SUBSTRATE:
            return Config.FRONTIER_RPC
        if Config.RUN_MODE == Config.MODE_GANACHE:
            return Config.GANACHE_RPC

    @classmethod
    def get_second_rpc(cls):
        if Config.RUN_MODE == Config.MODE_SUBSTRATE:
            return Config.SECOND_FRONTIER_RPC
        if Config.RUN_MODE == Config.MODE_GANACHE:
            return Config.SECOND_GANACHE_RPC

    @classmethod
    def get_api_and_deployer(cls):
        return get_eth_api_and_account(cls.get_first_rpc())

    @classmethod
    def get_api_and_deployer_second(cls):
        return get_eth_api_and_account(cls.get_second_rpc())

    @classmethod
    def transfer_balance(cls, receiver: str, amount: int):
        if Config.RUN_MODE == Config.MODE_SUBSTRATE:
            transfer_balance_substrate(Config.SUBSTRATE_WS, Config.SUBSTRATE_DONOR, {'ethereum': receiver}, amount)
        if Config.RUN_MODE == Config.MODE_GANACHE:
            transfer_balance_eth(Config.GANACHE_RPC, Config.GANACHE_DONOR, receiver, amount)

    @classmethod
    def transfer_balance_second(cls, receiver: str, amount: int):
        if Config.RUN_MODE == Config.MODE_SUBSTRATE:
            transfer_balance_substrate(
                Config.SECOND_SUBSTRATE_WS, Config.SUBSTRATE_DONOR, {'ethereum': receiver}, amount
            )
        if Config.RUN_MODE == Config.MODE_GANACHE:
            transfer_balance_eth(Config.SECOND_GANACHE_RPC, Config.GANACHE_DONOR, receiver, amount)
