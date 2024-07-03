from ruamel.yaml import YAML
import sys
import shutil
import json

from tests.util import get_contract_cache, get_eth_api_and_account, transfer_balance_eth
from src.util import ContractHelper, ContractWrapper

eth_chain_id = 0
relay_chain_id = 0

RELAY_RPC = 'http://127.0.0.1:18545'
ETH_RPC = 'http://127.0.0.1:28545'
DONOR_KEY = '0x4c0883a69102937d6231471b5dbb6204fe512961708279d7d9d1e6b5b9456d11'

try:
    relay_api, _ = get_eth_api_and_account(RELAY_RPC)
    eth_api, _ = get_eth_api_and_account(ETH_RPC)
    eth_chain_id = int(eth_api.eth.chain_id)
    relay_chain_id = int(relay_api.eth.chain_id)
except Exception:
    pass


if eth_chain_id != 1 or relay_chain_id != 47803:
    shutil.copy('./testnet/docker-compose.example.yml', './testnet/docker-compose.yml')
    print('Before start you need to run inside testnet directory:\ndocker-compose.yml up -d relay-node eth-node')
    sys.exit(0)


def transfer_erc20(erc20: ContractWrapper, from_address: str, to_address: str, amount: int = 100):
    erc20.execute_tx('approve', (from_address, amount * 10 ** 18), {'from': from_address})
    erc20.execute_tx('transferFrom', (from_address, to_address, amount * 10 ** 18), {'from': from_address})


yaml = YAML()

with open('./testnet/docker-compose.example.yml', 'r', encoding='utf-8') as f:
    compose = yaml.load(f)


eth_api, eth_deployer = get_eth_api_and_account(ETH_RPC)
relay_api, relay_deployer = get_eth_api_and_account(RELAY_RPC)

state = {'eth': {}, 'relay': {}}

print('Eth deployer private key:', eth_deployer.key.hex())
state['eth']['deployer'] = eth_deployer.key.hex()
print('Relay deployer private key:', relay_deployer.key.hex())
state['relay']['deployer'] = relay_deployer.key.hex()

transfer_balance_eth(ETH_RPC, DONOR_KEY, eth_deployer.address, 100)
transfer_balance_eth(RELAY_RPC, DONOR_KEY, relay_deployer.address, 100)

cached = get_contract_cache('0.8.24')

deployed = ContractHelper.deploy_by_bytecode(
    eth_api, eth_deployer, (eth_deployer.address,),
    abi=cached['bridge_linked']['abi'], bytecode=cached['bridge_linked']['bin']
)
print(f'Ethereum bridge address: {deployed["address"]}')
state['eth']['bridge'] = deployed['address']

eth_bridge = ContractWrapper(eth_api, deployed['address'], deployed['abi'])

deployed = ContractHelper.deploy_by_bytecode(
    eth_api, eth_deployer, (eth_deployer.address,),
    abi=cached['bridge_linked']['abi'], bytecode=cached['bridge_linked']['bin']
)
print(f'Relay bridge address: {deployed["address"]}')
state['relay']['bridge'] = deployed['address']

relay_bridge = ContractWrapper(relay_api, deployed['address'], deployed['abi'])

relay_signer = relay_api.eth.account.create()
relay_validator = relay_api.eth.account.create()
print(f'Relay signer private key: {relay_signer.key.hex()}')
state['relay']['signer'] = relay_signer.key.hex()
print(f'Relay validator private key: {relay_validator.key.hex()}')
state['relay']['validator'] = relay_validator.key.hex()

relay_bridge.execute_tx('setSigner', (relay_signer.address,), {'from': relay_deployer.address})
relay_bridge.execute_tx('addValidators', ([relay_validator.address],), {'from': relay_deployer.address})
transfer_balance_eth(RELAY_RPC, DONOR_KEY, relay_signer.address, 30)
transfer_balance_eth(RELAY_RPC, DONOR_KEY, relay_validator.address, 30)

# Set required confirmations
relay_bridge.execute_tx('setRequiredConfirmations', (1,),{'from': relay_deployer.address})

compose['services']['relay-bridge-validator']['environment']['ETH_CONTRACT_ADDRESS'] = state['relay']['bridge']
compose['services']['relay-bridge-validator']['environment']['ETH_PRIVATE_KEY'] = state['relay']['validator']

compose['services']['relay-bridge-signer-transactor']['environment']['ETH_CONTRACT_ADDRESS'] = state['relay']['bridge']
compose['services']['relay-bridge-signer-transactor']['environment']['ETH_PRIVATE_KEY'] = state['relay']['signer']

compose['services']['relay-bridge-signer-lister']['environment']['ETH_CONTRACT_ADDRESS'] = state['eth']['bridge']
compose['services']['relay-bridge-signer-lister']['environment']['ETH_PRIVATE_KEY'] = state['relay']['signer']

with open('./testnet/docker-compose.yml', 'w', encoding='utf-8') as f:
    yaml.dump(compose, f)
print('docker-compose.yml created')

with open('./testnet/state.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(state, indent=2, ensure_ascii=False))
print('state.json created')

with open('./testnet/urls.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(
        {relay_chain_id: ['http://relay-node:8545'], eth_chain_id: ['http://eth-node:8545']},
        indent=2, ensure_ascii=False
    ))
print('urls.json created')
