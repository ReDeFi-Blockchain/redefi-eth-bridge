from ruamel.yaml import YAML
import sys

from tests.util import get_contract_cache, get_eth_api_and_account, eth_add_to_auto_sign, transfer_balance_substrate
from src.util import ContractHelper, ContractWrapper

if '-h' in sys.argv or '--help' in sys.argv:
    print(
        f'Usage:\n  {sys.orig_argv[0]} {sys.argv[0]} [RPC_URL] [SUBSTRATE_WS_URL]\nExample:'
        f'\n  {sys.orig_argv[0]} {sys.argv[0]}'
        f'\n  {sys.orig_argv[0]} {sys.argv[0]} http://node.local'
        f'\n  {sys.orig_argv[0]} {sys.argv[0]} http://node.local ws://ws.local'
    )
    sys.exit(0)

yaml = YAML()

with open('docker-compose.example.yml', 'r', encoding='utf-8') as f:
    compose = yaml.load(f)

RPC_URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:9944'
SUBSTRATE_WS_URL = sys.argv[2] if len(sys.argv) > 2 else 'ws' + RPC_URL[4:]
print(f'RPC url: {RPC_URL}\nSubstrate WS url: {SUBSTRATE_WS_URL}')


api, deployer = get_eth_api_and_account(RPC_URL)
print('Deployer private key:', deployer.key.hex())
users = {'signer': api.eth.account.create(), 'validator': api.eth.account.create()}
for user, amount in (
    (deployer, 100),
    (users['signer'], 100),
    (users['validator'], 10)
):
    transfer_balance_substrate(
        'ws' + RPC_URL[4:], '//Alice', {'ethereum': user.address}, amount
    )
cached = get_contract_cache('0.8.24')
deployed = ContractHelper.deploy_by_bytecode(
    api, deployer, ('Eth BAX', 'EBAX', 18, deployer.address, 1_000),
    abi=cached['erc20']['abi'], bytecode=cached['erc20']['bin']
)
print(f'EBAX ERC-20 address: {deployed["address"]}')
# ethereum_bax = ContractWrapper(api, deployed['address'], deployed['abi'])
#
deployed = ContractHelper.deploy_by_bytecode(
    api, deployer, ('Relay BAX', 'RBAX', 18, deployer.address, 1_000),
    abi=cached['erc20']['abi'], bytecode=cached['erc20']['bin']
)
print(f'RBAX ERC-20 address: {deployed["address"]}')
# relay_bax = ContractWrapper(api, deployed['address'], deployed['abi'])
#
deployed = ContractHelper.deploy_by_bytecode(
    api, deployer, (deployer.address,),
    abi=cached['bridge_multi_sig']['abi'], bytecode=cached['bridge_multi_sig']['bin']
)
print(f'Bridge address: {deployed["address"]}')
bridge = ContractWrapper(api, deployed['address'], deployed['abi'])


# Add signer account for money transfers
bridge.execute_tx(
    'setSigner', (users['signer'].address,),
    {'from': deployer.address}
)

# Add validator accounts
bridge.execute_tx(
    'addValidators',
    ([users['validator'].address],),
    {'from': deployer.address}
)

# Set required confirmations
bridge.execute_tx(
    'setRequiredConfirmations', (1,),
    {'from': deployer.address}
)

compose['services']['bridge-validator']['environment']['ETH_RPC'] = RPC_URL
compose['services']['bridge-validator']['environment']['ETH_RPC_POLL_LATENCY_MS'] = 3000
compose['services']['bridge-validator']['environment']['BRIDGE_CONTRACT_ADDRESS'] = bridge.address
compose['services']['bridge-validator']['environment']['VALIDATOR_PRIVATE_KEY'] = users['validator'].key.hex()


with open('docker-compose.yml', 'w', encoding='utf-8') as f:
    yaml.dump(compose, f)
print('docker-compose.yml created')
