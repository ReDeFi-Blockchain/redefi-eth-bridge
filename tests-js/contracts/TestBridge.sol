// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IBridge {
  function transfer(bytes32[] memory _txHashes) external;
  function addFunds(address _token, uint256 _amount) external payable;
  function withdrawFunds(address _token, uint256 _amount) external;
  function deposit(address _receiver, address _token, uint _amount, uint _targetChainId) external payable;
}
