import typing

from eth_typing.evm import HexStr, Hash32, AnyAddress as Address
from hexbytes import HexBytes


__all__ = ['TxHash', 'Address']

TxHash = typing.Union[HexStr, HexBytes, Hash32]
