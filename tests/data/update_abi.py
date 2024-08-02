import json
import os

if __name__ == '__main__':
    DATA_DIR = os.path.abspath(os.path.dirname(__file__))
    ABI_DIR = os.path.abspath(os.path.join(DATA_DIR, '..', '..', 'src', 'abi'))
    with open(os.path.join(DATA_DIR, 'cache', 'compiled_0.8.24.json'), 'r', encoding='utf-8') as f:
        bridge = json.loads(f.read())['bridge_linked']
    with open(os.path.join(ABI_DIR, 'BridgeLinked.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps({'abi': bridge['abi'], 'doc': bridge['doc']}, indent=2, ensure_ascii=False))
