import { expect } from 'chai';
import { getRessetableConfig } from '../../fixtures/resettable';
import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { Bridge, TestERC20 } from '../../typechain-types';
import { HardhatEthersSigner } from '@nomicfoundation/hardhat-ethers/signers';
import { getRessetableWithDataConfig, ListInfo } from '../../fixtures/resettableWithData';


let bridge: Bridge;
let owner: HardhatEthersSigner;
let signer: HardhatEthersSigner;

let user1: HardhatEthersSigner;
let user2: HardhatEthersSigner;

let token1: TestERC20;
let token2: TestERC20;
let nonRegisteredToken: TestERC20;

let validListInfo1: ListInfo;
let validListInfo2: ListInfo;



describe('Signer list', async () => {
  beforeEach(async () => {
    const config = await loadFixture(getRessetableWithDataConfig);
    [user1, user2] = config.users;
    [validListInfo1, validListInfo2] = config.data;

    ({owner, signer} = config);

    token1 = config.tokens.owned;
    token2 = config.tokens.nonOwned;
    nonRegisteredToken = config.tokens.nonRegistered;

    bridge = config.bridge.connect(signer)
  });

  it('can list cross transfer, Listed event emited', async () => {
    await expect(bridge.list([validListInfo1.data, validListInfo2.data]))
      .to.emit(bridge, 'Listed')
      .withArgs(validListInfo1.hash, validListInfo1.chainId)
      .to.emit(bridge, 'Listed')
      .withArgs(validListInfo2.hash, validListInfo2.chainId);

    const confirmationsTx1 = await bridge.confirmations(validListInfo1.hash);
    const confirmationsTx2 = await bridge.confirmations(validListInfo2.hash);

    expect(confirmationsTx1).to.deep.eq([user1.address, validListInfo1.amount, 1, false]);
    expect(confirmationsTx2).to.deep.eq([user2.address, validListInfo2.amount, 2, false]);
  });

  it('cannot list transfer of non registered token', async () => {
    const NON_REGISTERED_TOKEN_LI = [
      BigInt(await nonRegisteredToken.getAddress()),
      BigInt(user1.address),
      100n * 10n ** 18n,
      validListInfo1.chainId,
      BigInt(validListInfo1.hash),
    ];

    await expect(bridge.list([NON_REGISTERED_TOKEN_LI]))
      .revertedWith('bridge: trying to list unregistered token');
  });

  it('cannot list zero amount transfer', async () => {
    const ZERO_AMOUNT_TOKEN_LI = [
      BigInt(await token1.getAddress()),
      BigInt(user1.address),
      0n,
      validListInfo1.chainId,
      BigInt(validListInfo1.hash),
    ];

    await expect(bridge.list([ZERO_AMOUNT_TOKEN_LI]))
      .revertedWith('bridge: amount must be more than zero');
  });

  it('cannot list transfer twice', async () => {
    // cannot in one tx
    await expect(bridge.list([validListInfo1.data, validListInfo1.data]))
      .revertedWith('bridge: txHash already listed');

    // cannot in different txs
    await bridge.list([validListInfo1.data]);
    await expect(bridge.list([validListInfo1.data]))
      .revertedWith('bridge: txHash already listed');
  });
  
  it('non-signer cannot register cross transfer', async () => {
    // even owner can't
    await expect(bridge.connect(owner).list([validListInfo1.data]))
      .revertedWithoutReason();
  });
});

