import logging
import json
import os
import typing

import web3
import eth_account.account
from src import bridge_types as types, util


__all__ = ['Worker', 'WorkerConfig']


class WorkerConfig(object):
    eth_rpc: str = os.getenv('ETH_RPC', 'http://127.0.0.1:9944')
    eth_contract_address = os.getenv('ETH_CONTRACT_ADDRESS', util.ADDRESS_0)
    eth_private_key: typing.Optional[str] = os.getenv('ETH_PRIVATE_KEY', None) or None
    eth_block_confirmations: int = int(os.getenv('ETH_BLOCK_CONFIRMATIONS', '64'))
    _poll_latency: int = int(os.getenv('ETH_RPC_POLL_LATENCY_MS', '3000'))
    rpc_urls_file_path: str = os.getenv('ETH_RPC_URLS_FILE', None)
    _rpc_urls = None

    @property
    def poll_latency(self):
        return self._poll_latency / 1_000

    def load_rpc_urls(self):
        if self.rpc_urls_file_path is None:
            raise ValueError('Invalid rpc urls file')
        with open(self.rpc_urls_file_path, 'r', encoding='utf-8') as f:
            urls = json.loads(f.read())
        self._rpc_urls = {int(k): v for k, v in urls.items()}

    @property
    def rpc_urls(self) -> typing.Dict[int, typing.List[str]]:
        if self._rpc_urls is None:
            self.load_rpc_urls()
        return self._rpc_urls


class Worker(object):
    LOGGER_NAME = 'worker.base'

    def __init__(self, config: WorkerConfig = None, name: typing.Optional[str] = None):
        if config is None:
            config = WorkerConfig()
        self.config = config
        self.account = None
        self.api = self.construct_http_api(self.config.eth_rpc)
        if config.eth_private_key is not None:
            self.account = eth_account.account.Account.from_key(config.eth_private_key)
            util.eth_add_to_auto_sign(self.api, self.account)
        self.log = logging.getLogger(self.LOGGER_NAME)
        self.bridge = self.get_bridge_contract(
            self.api, self.config.eth_contract_address, poll_latency=self.config.poll_latency
        )
        self.chain_id = int(self.api.eth.chain_id)
        self.name = self.__class__.__name__.lower() if name is None else name

    @classmethod
    def construct_http_api(cls, rpc_url: str):
        return web3.Web3(web3.Web3.HTTPProvider(rpc_url))

    @classmethod
    def get_bridge_contract(cls, api: web3.Web3, contract_address: types.Address, poll_latency=1.0):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'abi', 'BridgeLinked.json'), 'r') as f:
            abi = json.loads(f.read())['abi']
            return util.ContractWrapper(
                api, contract_address, contract_abi=abi, poll_latency=poll_latency
            )

    @classmethod
    def check_tx_block(cls, tx_hash: types.TxHash, rpc_url: str) -> typing.Optional[int]:
        api = cls.construct_http_api(rpc_url)

        tx_receipt = api.eth.get_transaction_receipt(tx_hash)
        if tx_receipt is None:
            return None
        return tx_receipt['blockNumber']

    def listen_blocks(self, last_block: int = 0) -> int:
        pass

    def listen(self):
        last_block = self.get_last_block()
        class_name = self.__class__.__name__.lower()

        while True:
            previous = last_block
            last_block = self.listen_blocks(last_block)
            self.save_last_block(last_block)
            self.log.info(f'[worker.{class_name}.{self.name}] Scanned blocks {previous} - {last_block}')

    @property
    def last_block_file_path(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            '..', '..', 'data', f'last_block_{self.__class__.__name__.lower()}_{self.name}.json'
        ))

    def save_last_block(self, last_block_number: int):
        copy_path = f'{self.last_block_file_path}.copy'
        with open(copy_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(last_block_number))
        os.rename(copy_path, self.last_block_file_path)

    def get_last_block(self):
        if not os.path.exists(self.last_block_file_path):
            return 0
        with open(self.last_block_file_path, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
