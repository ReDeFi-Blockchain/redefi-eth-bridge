import unittest

from tests.config import Config
from src.workers.base import Worker
from tests.util import get_eth_api_and_account, transfer_balance_substrate


class WorkerTestCase(unittest.TestCase):
    def test_check_tx_block(self):
        api, account = get_eth_api_and_account(Config.FRONTIER_RPC)
        transfer_balance_substrate(Config.SUBSTRATE_WS, Config.SUBSTRATE_DONOR, {'ethereum': account.address}, 50)
        user = api.eth.account.create()
        self.assertEqual(api.eth.get_balance(user.address), 0)
        value = 3 * 10 ** 16
        tx_hash = api.eth.send_transaction({
            "from": account.address,
            "value": value,
            "to": user.address
        })
        tx_receipt = api.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(api.eth.get_balance(user.address), value)
        block_number = Worker.check_tx_block(tx_hash, Config.FRONTIER_RPC)
        self.assertEqual(block_number, tx_receipt['blockNumber'])

