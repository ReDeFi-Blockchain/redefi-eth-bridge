import json
import os
import typing

import web3
from web3.middleware.signing import construct_sign_and_send_raw_middleware
import eth_account.account
import substrateinterface

from src.util import ContractHelper, evm_to_address


__all__ = ['transfer_balance_substrate', 'get_eth_api_and_account', 'eth_add_to_auto_sign', 'get_cache']


DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

CONTRACTS_PATH = os.path.join(DATA_DIR, '..', '..', 'contracts')


class CrossAccountId(typing.TypedDict):
    substrate: typing.NotRequired[str]
    ethereum: typing.NotRequired[str]


def cache_path(solc_version='0.8.24'):
    return os.path.join(DATA_DIR, 'cache', f'compiled_{solc_version}.json')


def build_cache(solc_version='0.8.24'):
    with open(os.path.join(CONTRACTS_PATH, 'Bridge.sol'), 'r', encoding='utf-8') as f:
        bridge_interface = ContractHelper.compile(f.read(), solc_version=solc_version, contract_name='Bridge')
    with open(os.path.join(CONTRACTS_PATH, 'BridgeMultiSig.sol'), 'r', encoding='utf-8') as f:
        multi_sig_interface = ContractHelper.compile(f.read(), solc_version=solc_version, contract_name='Bridge')
    with open(os.path.join(DATA_DIR, 'erc20.sol'), 'r', encoding='utf-8') as f:
        erc20_interface = ContractHelper.compile(f.read(), solc_version=solc_version, contract_name='Token')
    cache_data = {
        'erc20': erc20_interface,
        'bridge': bridge_interface,
        'bridge_multi_sig': multi_sig_interface
    }
    os.makedirs(os.path.join(DATA_DIR, 'cache'), exist_ok=True)
    with open(cache_path(solc_version), 'w', encoding='utf-8') as f:
        f.write(json.dumps(cache_data, indent=2))
    return cache_data


def get_cache(solc_version='0.8.24'):
    file_path = cache_path(solc_version)

    if not os.path.exists(file_path):
        build_cache(solc_version)

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())


def transfer_balance_substrate(
    ws_url: str, substrate_donor_seed: str, receiver: CrossAccountId, tokens: int = 1
):
    substrate_receiver = (
        evm_to_address(receiver['ethereum']) if receiver.get('substrate') is None else receiver['substrate']
    )
    with substrateinterface.SubstrateInterface(ws_url) as sub_api:
        one_token = 10 ** sub_api.properties['tokenDecimals']
        donor = substrateinterface.Keypair.create_from_uri(substrate_donor_seed)

        extrinsic = sub_api.create_signed_extrinsic(
            call=sub_api.compose_call(
                call_module='Balances', call_function='transfer_keep_alive',
                call_params={'dest': substrate_receiver, 'value': tokens * one_token}
            ), keypair=donor
        )

        sub_api.submit_extrinsic(extrinsic, wait_for_inclusion=True)


def get_eth_api_and_account(rpc_url: str) -> typing.Tuple[web3.Web3, eth_account.account.LocalAccount]:
    api = web3.Web3(web3.Web3.HTTPProvider(rpc_url))
    account = api.eth.account.create()
    api.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
    return api, account


def eth_add_to_auto_sign(api: web3.Web3, account: eth_account.account.LocalAccount):
    api.middleware_onion.add(construct_sign_and_send_raw_middleware(account))