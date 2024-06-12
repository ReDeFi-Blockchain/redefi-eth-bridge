# ReDeFi Ethereum bridge

## Install

To work with the bridge, Python 3.11 is required (Python 3.12 and above still do not have a built binding for [py-substrate-interface](https://github.com/polkascan/py-substrate-interface)).

The simplest way to install it is by using [pyenv](https://github.com/pyenv/pyenv) and [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv).

```shell
$ pyenv install 3.11
$ pyenv virtualenv 3.11 redefi-bridge
$ pyenv activate redefi-bridge
(redefi-bridge)$ pip install -r requirements.txt
```

## Launching the testnet

Launching the testnet is done in two stages. The first launch, using `launch_on_testnet.py`, will create a `docker-compose.yml` file with nodes based on [Ganache](https://www.npmjs.com/package/ganache).

```shell
(redefi-bridge)$ python launch_on_testnet.py
$ cd testnet
$ docker-compose up -d relay-node eth-node
```

The second run of launch_on_testnet.py will deploy all the necessary contracts to the nodes, as well as distribute balances to the validator and signer.

```shell
(redefi-bridge)$ python launch_on_testnet.py
$ cd testnet
$ docker-compose up -d
```
