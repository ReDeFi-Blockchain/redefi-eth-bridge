// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/interfaces/IERC20.sol";
import "./TestBridge.sol";

contract ReentrancyWithdraw {
  IBridge public bridge;
  uint256 deposit;

  constructor(address _bridge) payable {
    bridge = IBridge(_bridge);
  }

  receive() external payable {
    this.attackWithdraw();
  }

  function addFunds(uint256 _amount) external {
    deposit = _amount;
    bridge.addFunds{value: _amount}(address(0), _amount);
  }

  function attackWithdraw() external payable {
    uint256 bridgeBalance = address(bridge).balance;
    uint256 withdraw = bridgeBalance > deposit 
      ? deposit
      : bridgeBalance;

    try bridge.withdrawFunds(address(0), withdraw) {}
    catch {}
  }
}
