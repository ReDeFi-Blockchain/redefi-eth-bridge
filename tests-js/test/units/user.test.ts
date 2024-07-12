import { expect, use } from 'chai';
import { getRessetableConfig } from '../../fixtures/resettable';
import { ethers } from 'hardhat';
import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { Bridge, TestERC20 } from '../../typechain-types';
import { HardhatEthersSigner } from '@nomicfoundation/hardhat-ethers/signers';

let bridge: Bridge;
let owner: HardhatEthersSigner;
let user: HardhatEthersSigner;
let tokens: TestERC20[];
let ownedToken: TestERC20;
let nonOwnedToken: TestERC20;
let nonRegisteredToken: TestERC20;
const nativeTokenAddress = ethers.ZeroAddress;
const ADD_FUND_VALUE = 10_000_000n * (10n ** 18n);
const ADD_NATIVE_FUND_VALUE = 5000n * (10n ** 18n);


describe('User', () => {
  beforeEach(async () => {
    ({bridge, owner, user, tokens} = await loadFixture(getRessetableConfig));
    [ownedToken, nonOwnedToken, nonRegisteredToken] = tokens;
  
    // token1 is owned by the bridge
    await ownedToken.connect(owner).transferOwnership(bridge);
  
    // register native and erc-20 token
    await bridge.connect(owner).registerTokens([
      ownedToken, nonOwnedToken, nativeTokenAddress
    ]);
  
    // all the transactions performed by the user
    bridge = bridge.connect(user);
    ownedToken = ownedToken.connect(user);
    nonOwnedToken = nonOwnedToken.connect(user);
    nonRegisteredToken = nonRegisteredToken.connect(user);
  });

  it('can add ERC-20 funds to registered token', async () => {
    await expect(nonOwnedToken.approve(bridge, ADD_FUND_VALUE))
      .emit(nonOwnedToken, 'Approval')
      .withArgs(user, bridge, ADD_FUND_VALUE);

    // TODO add events?
    await bridge.addFunds(nonOwnedToken, ADD_FUND_VALUE);
    // TODO get account balance
  });

  it('can add native-token funds to registered token, msg.value should be equal to amount', async () => {
    // TODO cannot addToken with zero address
    await bridge.addFunds(nativeTokenAddress, ADD_NATIVE_FUND_VALUE, {value: ADD_NATIVE_FUND_VALUE});
    // TODO check balance
  });

  it('cannot add funds to non-registered token', async () => {
    await nonRegisteredToken.approve(bridge, ADD_FUND_VALUE);
    await expect(bridge.addFunds(nonRegisteredToken, ADD_FUND_VALUE))
      .revertedWith('bridge: token should be registered first');
  });

  it('cannot add zero funds', async () => {
    await expect(bridge.addFunds(nonOwnedToken, 0))
      .revertedWith('bridge: amount must be greater than zero');
  });

  it('cannot add more ERC-20 funds than approved', async () => {
    const APPROVE_VALUE = ADD_FUND_VALUE - 1n;
  
    await expect(nonOwnedToken.approve(bridge, APPROVE_VALUE))
      .emit(nonOwnedToken, 'Approval')
      .withArgs(user, bridge, APPROVE_VALUE);

    await expect(bridge.addFunds(nonOwnedToken, ADD_FUND_VALUE))
      .revertedWith('TransferHelper: TRANSFER_FROM_FAILED');
  });

  it('cannot add more ERC-20 funds than have', async () => {
    const balance = await nonOwnedToken.balanceOf(user);
    expect(balance).to.be.gt(0);

    // Approve gt Fund value, but fund value gt balance
    const APPROVE_VALUE = balance + 2000n;
    const FUND_VALUE = balance + 1000n;

    await expect(nonOwnedToken.approve(bridge, APPROVE_VALUE))
      .emit(nonOwnedToken, 'Approval')
      .withArgs(user, bridge, APPROVE_VALUE);

    await expect(bridge.addFunds(nonOwnedToken, FUND_VALUE))
      .revertedWith('TransferHelper: TRANSFER_FROM_FAILED');
  });

  it('cannot add more natvive-tokens than msg.value', async () => {
    const msgValue = ADD_NATIVE_FUND_VALUE - 1n;

    await expect(bridge.addFunds(
      nativeTokenAddress, ADD_NATIVE_FUND_VALUE, {value: msgValue}
    )).revertedWith('bridge: invalid amount');
  });

  it('cannot add funds to token owned by the bridge', async () => {
    await expect(bridge.addFunds(ownedToken, 1))
      .revertedWith('bridge: no need any funds for owned tokens');
  });

  it('cannot add funds to bridge under the maintenance mode', async () => {
    await bridge.connect(owner).switchMaintenance(true);

    await expect(bridge.addFunds(nonOwnedToken, ADD_FUND_VALUE))
      .revertedWithoutReason();
  });
});
