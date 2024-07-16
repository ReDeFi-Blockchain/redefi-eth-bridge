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
const TRANSFER_VALUE = 10_000_000n * (10n ** 18n);
const TRANSFER_NATIVE_VALUE = 5000n * (10n ** 18n);
const TARGER_CHAIN_ID = 1899;


describe('Deposit', () => {
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

  it('user can deposit native tokens, Deposit event emited', async () => {
    await expect(
      bridge.deposit(user, nativeTokenAddress, TRANSFER_NATIVE_VALUE, TARGER_CHAIN_ID, {value: TRANSFER_NATIVE_VALUE})
    )
      .to.emit(bridge, "Deposit")
      .withArgs(nativeTokenAddress, user, TRANSFER_NATIVE_VALUE, TARGER_CHAIN_ID);
  });

  it('user cannot deposit native tokens if amount != value', async () => {
    const WRONG_VALUE = TRANSFER_NATIVE_VALUE - 1n;
    // no value
    await expect(
      bridge.deposit(user, nativeTokenAddress, TRANSFER_NATIVE_VALUE, TARGER_CHAIN_ID) 
    )
      .revertedWith('bridge: invalid amount')
    // wrong value
    await expect(
      bridge.deposit(user, nativeTokenAddress, TRANSFER_NATIVE_VALUE, TARGER_CHAIN_ID, {value: WRONG_VALUE}) 
    )
      .revertedWith('bridge: invalid amount')
  });

  it('user can deposit "isOwn=false" ERC20 tokens, Deposit event emited', async () => {
    await nonOwnedToken.approve(bridge, TRANSFER_VALUE);

    await expect(
      bridge.deposit(user, nonOwnedToken, TRANSFER_VALUE, TARGER_CHAIN_ID)
    )
      .to.emit(bridge, "Deposit")
      .withArgs(nonOwnedToken, user, TRANSFER_VALUE, TARGER_CHAIN_ID);
  });

  it('user can deposit "isOwn=true" ERC20 tokens, Deposit event emited', async () => {
    await ownedToken.approve(bridge, TRANSFER_VALUE);

    await expect(
      bridge.deposit(user, ownedToken, TRANSFER_VALUE, TARGER_CHAIN_ID)
    )
      .to.emit(bridge, "Deposit")
      .withArgs(ownedToken, user, TRANSFER_VALUE, TARGER_CHAIN_ID);
  });

  it('user cannot deposit "isOwn=true" ERC20 tokens if allowance low', async () => {
    await expect(
      bridge.deposit(user, ownedToken, TRANSFER_VALUE, TARGER_CHAIN_ID)
    )
      .revertedWithCustomError(ownedToken, 'ERC20InsufficientAllowance');
  });

  it('user cannot deposit "isOwn=false" ERC20 tokens if balance low', async () => {
    const balance = await nonOwnedToken.balanceOf(user);
    const WRONG_AMOUNT = balance + 1n;
    await nonOwnedToken.approve(bridge, WRONG_AMOUNT);

    await expect(
      bridge.deposit(user, nonOwnedToken, WRONG_AMOUNT, TARGER_CHAIN_ID)
    )
      .revertedWith('TransferHelper: TRANSFER_FROM_FAILED');
  });

  it('if deposited token "isOwn" it will be burnFrom', async () => {
    await ownedToken.approve(bridge, TRANSFER_VALUE);

    // Transfer event to zero address means burnFrom called
    await expect(
      bridge.deposit(user, ownedToken, TRANSFER_VALUE, TARGER_CHAIN_ID)
    )
      .to.emit(ownedToken, 'Transfer')
      .withArgs(user, ethers.ZeroAddress, TRANSFER_VALUE);
  });

  it('if deposited token "isOwn=false" it will be transferFrom to bridge\'s account', async () => {
    await nonOwnedToken.approve(bridge, TRANSFER_VALUE);

    // Transfer event to bridge's address means transferFrom called
    await expect(
      bridge.deposit(user, nonOwnedToken, TRANSFER_VALUE, TARGER_CHAIN_ID)
    )
      .to.emit(nonOwnedToken, 'Transfer')
      .withArgs(user, bridge, TRANSFER_VALUE);
  });

  it('user cannot deposit if maintenance mode enabled', async () => {
    await nonOwnedToken.approve(bridge, TRANSFER_VALUE);
    await bridge.connect(owner).switchMaintenance(true);

    await expect(
      bridge.deposit(user, nonOwnedToken, TRANSFER_VALUE, TARGER_CHAIN_ID)
    )
      .revertedWithoutReason();
  });

  it('user cannot deposit zero amount', async () => {
    await nonOwnedToken.approve(bridge, TRANSFER_VALUE);
    const ZERO = 0n;

    await expect(
      bridge.deposit(user, nonOwnedToken, ZERO, TARGER_CHAIN_ID)
    )
      .revertedWith('bridge: amount must be greater than zero');
  });

  it('smart contracts (wallets) can deposit tokens', async () => {
    const walletNativeBalance = 30n * (10n ** 18n);
    const deposit = 10n * (10n ** 18n);

    const WalletFactory = await ethers.getContractFactory('TestWallet');
    const wallet = await WalletFactory.connect(user).deploy(bridge, {value: walletNativeBalance});

    await expect(wallet.connect(user).depositToBridge(user, nativeTokenAddress, deposit, 1899))
      .to.emit(bridge, 'Deposit');
  });

  it('receiver cannot be zero address', async () => {
    await nonOwnedToken.approve(bridge, TRANSFER_VALUE);

    await expect(
      bridge.deposit(ethers.ZeroAddress, nonOwnedToken, TRANSFER_VALUE, TARGER_CHAIN_ID)
    )
      .revertedWith('bridge: zero receiver');
  });

  it('cannot deposit unregistered token', async () => {
    await nonRegisteredToken.approve(bridge, TRANSFER_VALUE);

    await expect(
      bridge.deposit(user, nonRegisteredToken, TRANSFER_VALUE, TARGER_CHAIN_ID)
    )
      .revertedWith('bridge: unable to deposit unregistered token');
  });
})