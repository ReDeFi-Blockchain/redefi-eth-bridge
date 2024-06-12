from tests.base import EthTestCase
from tests.config import Config
from src.workers.base import Worker


class WorkerTestCase(EthTestCase):
    def test_check_tx_block(self):
        api, account = self.get_api_and_deployer()
        self.transfer_balance(account.address, 50)
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
        block_number = Worker.check_tx_block(
            tx_hash, Config.FRONTIER_RPC if Config.RUN_MODE == Config.MODE_SUBSTRATE else Config.GANACHE_RPC
        )
        self.assertEqual(block_number, tx_receipt['blockNumber'])

