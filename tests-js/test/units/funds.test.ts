import { expect } from 'chai';
import { getRessetableConfig } from '../../fixtures/resettable';
import { ethers } from 'hardhat';
import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { Bridge, TestERC20 } from '../../typechain-types';
import { HardhatEthersSigner } from '@nomicfoundation/hardhat-ethers/signers';
import { getRessetableWithDataConfig } from '../../fixtures/resettableWithData';

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

    const addFundsTx = bridge.addFunds(nonOwnedToken, ADD_FUND_VALUE);
    await expect(addFundsTx)
      .emit(bridge, 'Funded')
      .withArgs(user, nonOwnedToken, ADD_FUND_VALUE, false);

    await expect(addFundsTx)
      .changeTokenBalances(
        nonOwnedToken,
        [bridge, user],
        [ADD_FUND_VALUE, -ADD_FUND_VALUE]
      );
  });

  it('can add native-token funds to registered token, msg.value should be equal to amount', async () => {
    const addFundsTx = bridge.addFunds(nativeTokenAddress, ADD_NATIVE_FUND_VALUE, {value: ADD_NATIVE_FUND_VALUE});
    await expect(addFundsTx)
      .emit(bridge, 'Funded')
      .withArgs(user, nativeTokenAddress, ADD_NATIVE_FUND_VALUE, false);

    await expect(addFundsTx)
      .changeEtherBalances(
        [bridge, user],
        [ADD_NATIVE_FUND_VALUE, -ADD_NATIVE_FUND_VALUE]
      );
  });

  it('cannot deposit native tokens to bridge directly', async () => {
    await expect(user.sendTransaction({to: bridge, value: ADD_NATIVE_FUND_VALUE}))
      .revertedWithoutReason();
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

  it('can withdraw ERC-20 funds if balance enough', async () => {
    await nonOwnedToken.approve(bridge, ADD_FUND_VALUE);
    await bridge.addFunds(nonOwnedToken, ADD_FUND_VALUE);

    const withdrawFundsTx = bridge.withdrawFunds(nonOwnedToken, ADD_FUND_VALUE);

    await expect(withdrawFundsTx)
      .to.emit(bridge, 'Funded')
      .withArgs(user, nonOwnedToken, ADD_FUND_VALUE, true);

    await expect(withdrawFundsTx)
      .changeTokenBalances(
        nonOwnedToken, 
        [bridge, user],
        [-ADD_FUND_VALUE, ADD_FUND_VALUE]
      );
  });

  it('can partially withdraw ERC-20 funds if balance enough', async () => {
    const FIRST_WITHDRAW = 1n;
    const SECOND_WITHDRAW = ADD_FUND_VALUE - FIRST_WITHDRAW;
    // 3 withdraw exceeds deposit
    const THIRD_WITHDRAW = 1n;

    await nonOwnedToken.approve(bridge, ADD_FUND_VALUE);
    await bridge.addFunds(nonOwnedToken, ADD_FUND_VALUE);

    const withdrawFundsTx = bridge.withdrawFunds(nonOwnedToken, FIRST_WITHDRAW);
    await expect(withdrawFundsTx)
      .changeTokenBalances(
        nonOwnedToken, 
        [bridge, user],
        [-FIRST_WITHDRAW, FIRST_WITHDRAW]
      );

    await expect(withdrawFundsTx)
      .to.emit(bridge, 'Funded')
      .withArgs(user, nonOwnedToken, FIRST_WITHDRAW, true);

    await expect(bridge.withdrawFunds(nonOwnedToken, SECOND_WITHDRAW))
      .changeTokenBalances(
        nonOwnedToken, 
        [bridge, user],
        [-SECOND_WITHDRAW, SECOND_WITHDRAW]
      );
    
    await expect(bridge.withdrawFunds(nonOwnedToken, THIRD_WITHDRAW))
      .revertedWith('bridge: invalid amount');
  });

  it('can withdraw native funds if balance enough', async () => {
    await bridge.addFunds(nativeTokenAddress, ADD_NATIVE_FUND_VALUE, {value: ADD_NATIVE_FUND_VALUE});

    const withdrawFundsTx = bridge.withdrawFunds(nativeTokenAddress, ADD_NATIVE_FUND_VALUE);

    await expect(withdrawFundsTx)
      .to.emit(bridge, 'Funded')
      .withArgs(user, nativeTokenAddress, ADD_NATIVE_FUND_VALUE, true);
      
    await expect(withdrawFundsTx)
      .changeEtherBalances(
        [bridge, user],
        [-ADD_NATIVE_FUND_VALUE, ADD_NATIVE_FUND_VALUE]
      )
    
    // cannot withdraw more tokens
    await expect(bridge.withdrawFunds(nativeTokenAddress, 1))
      .revertedWith('bridge: invalid amount')
  });

  it.skip('[TODO: if token removal will be added] can withdraw removed token', async () => {});

  it('cannot withdraw 0 amount', async () => {
    await nonOwnedToken.approve(bridge, ADD_FUND_VALUE);
    await bridge.addFunds(nonOwnedToken, ADD_FUND_VALUE);

    await expect(bridge.withdrawFunds(nonOwnedToken, 0))
      .revertedWith('bridge: amount must be greater than zero');
  });

  it('cannot withdraw from non-registered token', async () => {
    await expect(bridge.withdrawFunds(nonRegisteredToken, 1))
      .rejectedWith('bridge: token should be registered first');
  });

  it('cannot withdraw token owned by the bridge', async() => {
    await expect(bridge.withdrawFunds(ownedToken, 1))
      .rejectedWith('bridge: no need any funds for owned tokens');
  });

  it('cannot withdraw more than deposited', async () => {
    await nonOwnedToken.approve(bridge, ADD_FUND_VALUE);
    await bridge.addFunds(nonOwnedToken, ADD_FUND_VALUE);

    await expect(bridge.withdrawFunds(nonOwnedToken, ADD_FUND_VALUE + 1n))
      .revertedWith('bridge: invalid amount');
  });

  it('cannot withdraw if bridge\'s balance of ERC-20 less than amount', async () => {
    const {users, tokens, validator, owner, signer} = await loadFixture(getRessetableWithDataConfig);
    const bridgeBalanceBefore = await tokens.nonOwned.balanceOf(bridge);
    await bridge.connect(owner).setRequiredConfirmations(1);

    const [funder, recepient] = users;

    // funder added 500
    await tokens.nonOwned.connect(funder).approve(bridge, 500n);
    await bridge.connect(funder).addFunds(tokens.nonOwned, 500n);

    // 100 tokens has been transfered
    const txHash = '0x9daa6e69e52c3f6ef8f4da8a88ec9ea031ee036c64f91ead13ca61fc054e1038';
    const transfer = [
      BigInt(await tokens.nonOwned.getAddress()),
      BigInt(recepient.address),
      bridgeBalanceBefore + 100n,
      9999,
      BigInt('0x9daa6e69e52c3f6ef8f4da8a88ec9ea031ee036c64f91ead13ca61fc054e1038'),
    ]

    // listed, validated and transfered
    await bridge.connect(signer).list([transfer]);
    await bridge.connect(validator).confirm([txHash]);
    await bridge.connect(signer).transfer([txHash]);

    // bridge balance = 400
    const bridgeBalanceAfter = await tokens.nonOwned.balanceOf(bridge);
    expect(bridgeBalanceAfter).to.eq(400);

    // funder cannot withdraw 500
    await expect(bridge.connect(funder).withdrawFunds(tokens.nonOwned, 500))
      .revertedWith('TransferHelper: TRANSFER_FAILED');
  });

  it('cannot perform reentrancy attack', async () => {
    const HACKER_INITIAL_VALUE = 300;
    const HACKER_DEPOSIT = 100;

    const ReentrancyFactory = await ethers.getContractFactory('ReentrancyWithdraw');
    const hacker = await ReentrancyFactory.connect(user).deploy(bridge, {value: HACKER_INITIAL_VALUE});

    await bridge.connect(owner).addFunds(nativeTokenAddress, 777, {value: 777});

    await hacker.addFunds(HACKER_DEPOSIT);

    // hacker cannot withdraw more than balance
    await expect(hacker.attackWithdraw({gasLimit: 10_000_000}))
      .changeEtherBalance(hacker, HACKER_DEPOSIT)
  });
});
