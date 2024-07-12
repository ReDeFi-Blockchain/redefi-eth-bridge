import { expect, use } from 'chai';
import { getRessetableConfig } from '../../fixtures/resettable';
import { ethers } from 'hardhat';
import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { Bridge, TestERC20 } from '../../typechain-types';
import { HardhatEthersSigner } from '@nomicfoundation/hardhat-ethers/signers';

let bridge: Bridge;
let owner: HardhatEthersSigner;
let user: HardhatEthersSigner;
let signers: HardhatEthersSigner[];
let nonOwnedToken: TestERC20;


describe.skip('Validator', async () => {
  beforeEach(async () => {
    ({bridge, owner, user, signers} = await loadFixture(getRessetableConfig));
  });


  it('can do something', async () => {

  });
});
