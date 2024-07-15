import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { Bridge } from '../../typechain-types';
import { HardhatEthersSigner } from '@nomicfoundation/hardhat-ethers/signers';
import { getRessetableWithDataConfig, ListInfo } from '../../fixtures/resettableWithData';
import { expect } from 'chai';

let bridge: Bridge;
let owner: HardhatEthersSigner;
let validator: HardhatEthersSigner;
let signer: HardhatEthersSigner;
let listInfo1: ListInfo;
let listInfo2: ListInfo;


describe('Validator', async () => {
  beforeEach(async () => {
    const config = await loadFixture(getRessetableWithDataConfig);
    ({validator, signer, owner} = config);
    [listInfo1, listInfo2] = config.data;
  
    bridge = config.bridge.connect(validator);
  });


  it('can confirm transfer transaction, Confirmed event emited', async () => {
    await bridge.connect(signer).list([listInfo1.data, listInfo2.data]);

    await expect(bridge.confirm([listInfo1.hash, listInfo2.hash]))
      .to.emit(bridge, 'Confirmed')
      .withArgs(listInfo1.hash, bridge.validatorIds(validator));

      const confirmedBy1 = await bridge.confirmedBy(listInfo1.hash);
      const confirmedBy2 = await bridge.confirmedBy(listInfo2.hash);
      expect(confirmedBy1).to.deep.eq([1]);
      expect(confirmedBy2).to.deep.eq([1]);

      expect(await bridge.isConfirmedBy(listInfo1.hash, validator));
      expect(await bridge.isConfirmedBy(listInfo2.hash, validator));
  });

  it('cannot confirm non-listed transfer', async () => {
    await expect(bridge.confirm([listInfo1.hash, listInfo2.hash]))
      .revertedWith('bridge: unknown txHash');
  });

  it.skip('[TODO] cannot confirm already sent transfer', async () => {

  });

  it('cannot confirmed transfer twice', async () => {
    await bridge.connect(signer).list([listInfo1.data, listInfo2.data]);

    // cannot confirm in one tx
    await expect(bridge.confirm([listInfo1.hash, listInfo1.hash]))
      .revertedWith('bridge: txHash already confirmed');

    await bridge.confirm([listInfo1.hash]);
    await expect(bridge.confirm([listInfo1.hash]))
      .revertedWith('bridge: txHash already confirmed');
  });

  it('Non-validator cannot confirm transfer transaction', async () => {
    // even owner can't
    await bridge.connect(signer).list([listInfo1.data]);

    // cannot confirm in one tx
    await expect(bridge.connect(owner).confirm([listInfo1.hash]))
      .revertedWithoutReason();
  });
});
