import unittest

from src.util import evm_to_address, address_to_evm


class EvmUtilTestCase(unittest.TestCase):
    def test_evm_to_address(self):
        self.assertEqual(
            evm_to_address('0x21187dc490c3250843508d482aBBcFD28270e715'),
            '5DGkcNrpY9uq19Y2Qk22t2xYDUMG7Gfdkq9q6TYo7gFFpKU7'
        )

    def test_address_to_evm(self):
        self.assertEqual(
            address_to_evm('5DGkcNrpY9uq19Y2Qk22t2xYDUMG7Gfdkq9q6TYo7gFFpKU7'),
            '0x356c72a03cf369873b7dd0cbc7079a47d10f4315'
        )