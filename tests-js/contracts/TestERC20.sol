// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract TestERC20 is ERC20, ERC20Burnable, Ownable {
  address admin;

  modifier onlyAdmin {
    require(msg.sender == owner() || msg.sender == admin);
    _;
  }

  constructor() ERC20("Redefi Token", "RED") Ownable(msg.sender) {
    // set initial balances
    uint256 initialBalance = 10_000_000e18;
    _mint(0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266, initialBalance);
    _mint(0x70997970C51812dc3A010C7d01b50e0d17dc79C8, initialBalance);
    _mint(0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC, initialBalance);
    _mint(0x90F79bf6EB2c4f870365E785982E1f101E93b906, initialBalance);
    _mint(0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65, initialBalance);
    _mint(0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc, initialBalance);
  }

  function setAdmin(address _admin) onlyOwner external {
    admin = _admin;
  }

  function mint(address account, uint256 value) external onlyAdmin {
    _mint(account, value);
  }
}