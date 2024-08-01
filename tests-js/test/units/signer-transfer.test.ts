import { expect } from 'chai';
import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { Bridge } from '../../typechain-types';
import { HardhatEthersSigner } from '@nomicfoundation/hardhat-ethers/signers';
import { getRessetableWithDataConfig, ListInfo } from '../../fixtures/resettableWithData';
import { ethers } from 'hardhat';


let bridge: Bridge;
let owner: HardhatEthersSigner;
let signer: HardhatEthersSigner;

let validator1: HardhatEthersSigner;
let validator2: HardhatEthersSigner;

let listInfoOwned: ListInfo;
let listInfoNonOwned: ListInfo;
let listInfoNative: ListInfo;

const nativeTokenAddress = ethers.ZeroAddress;

describe('Signer transfer', async () => {
  beforeEach(async () => {
    const config = await loadFixture(getRessetableWithDataConfig);
    ({bridge, owner, signer} = config);

    // reuired confirmation = 2
    await bridge.connect(owner).setRequiredConfirmations(2);

    validator1 = config.validator;
    [validator2] = config.users;
    await bridge.addValidators([validator2]);

    // list
    [listInfoOwned, listInfoNonOwned, listInfoNative] = config.data;
    await bridge.connect(signer).list([listInfoOwned.data, listInfoNonOwned.data, listInfoNative.data]);

    bridge = bridge.connect(signer);
  });

  it('can transfer native tokens if enough confirmations', async () => {
    // validated
    await bridge.connect(validator1).confirm([listInfoNative.hash]);
    await bridge.connect(validator2).confirm([listInfoNative.hash]);

    const transferTx = bridge.transfer([listInfoNative.hash]);

    await expect(transferTx)
      .to.emit(bridge, 'Transfer')
      .withArgs(listInfoNative.hash, listInfoNative.amount);
  
    await expect(transferTx)
      .to.changeEtherBalances(
        [bridge, listInfoNative.recepient],
        [-listInfoNative.amount, listInfoNative.amount]
      );

    const confirmationInfo = await bridge.confirmations(listInfoNative.hash);
    expect(confirmationInfo.isSent).to.be.true;
  });

  it('can transfer "isOwn" ERC20 tokens if enough confirmations', async () => {
    // validated
    await bridge.connect(validator1).confirm([listInfoOwned.hash]);
    await bridge.connect(validator2).confirm([listInfoOwned.hash]);

    const transferTx = bridge.transfer([listInfoOwned.hash]);

    // Bridge event
    await expect(transferTx)
      .to.emit(bridge, 'Transfer')
      .withArgs(listInfoOwned.hash, listInfoOwned.amount);
    
    // ERC20 events for mint because token is owned
    await expect(transferTx)
      .to.emit(listInfoOwned.token, 'Transfer')
      .withArgs(ethers.ZeroAddress, listInfoOwned.recepient, listInfoOwned.amount);
  
    await expect(transferTx)
      .to.changeTokenBalances(
        listInfoOwned.token,
        [bridge, listInfoOwned.recepient],
        [0, listInfoOwned.amount]
      );
    
    const confirmationInfo = await bridge.confirmations(listInfoOwned.hash);
    expect(confirmationInfo.isSent).to.be.true;  
  });

  it('can transfer "isOwn=false" ERC20 tokens if enough confirmations', async () => {
    // validated
    await bridge.connect(validator1).confirm([listInfoNonOwned.hash]);
    await bridge.connect(validator2).confirm([listInfoNonOwned.hash]);

    const transferTx = bridge.transfer([listInfoNonOwned.hash]);

    // Bridge event
    await expect(transferTx)
      .to.emit(bridge, 'Transfer')
      .withArgs(listInfoNonOwned.hash, listInfoNonOwned.amount);
    
    // ERC20 events for transfer because token is not owned
    await expect(transferTx)
      .to.emit(listInfoNonOwned.token, 'Transfer')
      .withArgs(bridge, listInfoNonOwned.recepient, listInfoNonOwned.amount);
  
    await expect(transferTx)
      .to.changeTokenBalances(
        listInfoNonOwned.token,
        [bridge, listInfoNonOwned.recepient],
        [-listInfoNonOwned.amount, listInfoNonOwned.amount]
      );

    const confirmationInfo = await bridge.confirmations(listInfoNonOwned.hash);
    expect(confirmationInfo.isSent).to.be.true;  
  });

  it('can transfer native and ERC20 tokens in one tx if enough confirmations', async () => {
    // validated native
    await bridge.connect(validator1).confirm([listInfoNative.hash]);
    await bridge.connect(validator2).confirm([listInfoNative.hash]);
    // validated owned ERC20
    await bridge.connect(validator1).confirm([listInfoOwned.hash]);
    await bridge.connect(validator2).confirm([listInfoOwned.hash]);
    // validate non-owned ERC20
    await bridge.connect(validator1).confirm([listInfoNonOwned.hash]);
    await bridge.connect(validator2).confirm([listInfoNonOwned.hash]);

    const transferTx = bridge.transfer(
      [listInfoNonOwned.hash, listInfoOwned.hash, listInfoNative.hash]
    );

    await expect(transferTx)
      .to.emit(bridge, 'Transfer')
      .withArgs(listInfoNative.hash, listInfoNative.amount)
      .to.emit(bridge, 'Transfer')
      .withArgs(listInfoOwned.hash, listInfoOwned.amount)
      .to.emit(bridge, 'Transfer')
      .withArgs(listInfoNonOwned.hash, listInfoNonOwned.amount);  
  });

  it('cannot transfer if confirmations less than requried', async () => {
    // not enough validations
    await bridge.connect(validator1).confirm([listInfoOwned.hash]);

    await expect(bridge.transfer([listInfoOwned.hash]))
      .to.not.emit(bridge, 'Transfer');
    
    const confirmationInfo = await bridge.confirmations(listInfoOwned.hash);
    expect(confirmationInfo.isSent).to.be.false;
  });

  it('cannot transfer already sent', async () => {
    // validated
    await bridge.connect(validator1).confirm([listInfoNative.hash]);
    await bridge.connect(validator2).confirm([listInfoNative.hash]);

    await bridge.transfer([listInfoNative.hash]);
    const confirmationInfo = await bridge.confirmations(listInfoNative.hash);
    expect(confirmationInfo.isSent).to.be.true;

    await expect(bridge.transfer([listInfoNative.hash]))
      .to.not.emit(bridge, 'Transfer');
  });

  it('cannot transfer unknown txHash', async () => {
    const UNKNOWN_TX_HASH = '0x9daa6e69e52c3f6ef8f4da8a88ec9ea031ee036c64f91ead13ca61fc054e1038';

    // even if zero confirmations
    await bridge.connect(owner).setRequiredConfirmations(0);

    await expect(bridge.transfer([UNKNOWN_TX_HASH])).revertedWithPanic();
  });

  it('cannot transfer native tokens if balance low', async () => {
    const txHash = '0x9daa6e69e52c3f6ef8f4da8a88ec9ea031ee036c64f91ead13ca61fc054e1038';
    const tooBigTransfer = [
        BigInt(nativeTokenAddress),
        BigInt(owner.address),
        10000n * (10n ** 18n),
        1899,
        BigInt(txHash),
      ]
    await bridge.list([tooBigTransfer]);

    await bridge.connect(validator1).confirm([txHash]);
    await bridge.connect(validator2).confirm([txHash]);

    await expect(bridge.transfer([txHash]))
      .revertedWith('TransferHelper: ETH_TRANSFER_FAILED');
  });

  it('cannot transfer ERC20 tokens if balance low', async () => {
    const txHash = '0x9daa6e69e52c3f6ef8f4da8a88ec9ea031ee036c64f91ead13ca61fc054e1038';
    const tooBigTransfer = [
        BigInt(await listInfoNonOwned.token.getAddress()),
        BigInt(owner.address),
        10000n * (10n ** 18n),
        1899,
        BigInt(txHash),
      ];

    await bridge.list([tooBigTransfer]);

    await bridge.connect(validator1).confirm([txHash]);
    await bridge.connect(validator2).confirm([txHash]);

    await expect(bridge.transfer([txHash]))
      .revertedWith('TransferHelper: TRANSFER_FAILED');
  });

  it('non-signer cannot transfer', async () => {
    // even owner can't
    await bridge.connect(validator1).confirm([listInfoNative.hash]);
    await bridge.connect(validator2).confirm([listInfoNative.hash]);

    await expect(bridge.connect(owner).transfer([listInfoNative.hash]))
      .revertedWithoutReason();
  });

  it('cannot perform reentrancy attack', async () => {
    const txHash = '0x9daa6e69e52c3f6ef8f4da8a88ec9ea031ee036c64f91ead13ca61fc054e1038';

    const balanceBridge = await ethers.provider.getBalance(bridge);
    // Suppose the attacker deposited half of the bridge's balance
    // We will check it is impossible to transfer the full amount
    const DEPOSIT = balanceBridge / 2n;

    // set reentrancy contract
    const ReentrancyFactory = await ethers.getContractFactory('ReentrancyTransfer');
    const reentrancy = await ReentrancyFactory.deploy(bridge);
    await reentrancy.setHashToTransfer(txHash);

    // the deposit listed by the signer
    await bridge.connect(signer).list([
      [
        BigInt(nativeTokenAddress),
        BigInt(await reentrancy.getAddress()),
        DEPOSIT,
        1899,
        BigInt(txHash)
      ]
    ]);

    // transfer was real, validators confirmed
    await bridge.connect(validator1).confirm([txHash]);
    await bridge.connect(validator2).confirm([txHash]);

    // even if the attacker got the signer role...
    await bridge.connect(owner).setSigner(reentrancy);

    // ...it cannot transfer more than deposit
    await reentrancy.attackTransfer();

    // bridge's balance correct
    const balanceBridgeAfterAttack = await ethers.provider.getBalance(bridge);
    expect(balanceBridgeAfterAttack).to.eq(balanceBridge - DEPOSIT);
  });
});

