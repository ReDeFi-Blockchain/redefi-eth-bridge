class BaseConfig(object):
    MODE_GANACHE = 'ganache'
    MODE_SUBSTRATE = 'substrate'

    RUN_MODE = MODE_SUBSTRATE

    FRONTIER_RPC = 'http://127.0.0.1:19944'
    SUBSTRATE_WS = 'ws://127.0.0.1:19944'
    SECOND_FRONTIER_RPC = 'http://127.0.0.1:9944'
    SECOND_SUBSTRATE_WS = 'ws://127.0.0.1:9944'
    SUBSTRATE_DONOR = '//Alice'

    GANACHE_RPC = 'http://127.0.0.1:18545'
    SECOND_GANACHE_RPC = 'http://127.0.0.1:28545'
    GANACHE_DONOR = '0x4c0883a69102937d6231471b5dbb6204fe512961708279d7d9d1e6b5b9456d11'
