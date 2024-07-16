// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./TestBridge.sol";
import "@openzeppelin/contracts/interfaces/IERC20.sol";

contract TestWallet {
  IBridge bridge;

  constructor(address _bridge) payable {
    bridge = IBridge(_bridge);
  }

  receive() external payable {}

  function approve(address _token, address _spender, uint256 _amount) external {
    IERC20(_token).approve(_spender, _amount);
  }

  function addFundsToBridge(address _token, uint256 _amount) external payable {
    uint256 value = _token == address(0) ? _amount : 0;
    bridge.addFunds{value: value}(_token, _amount);
  }

  function depositToBridge(address _receiver, address _token, uint _amount, uint _targetChainId) external {
    uint256 value = _token == address(0) ? _amount : 0;
    bridge.deposit{value: value}(_receiver, _token, _amount, _targetChainId);
  }
}