import { expect } from 'chai';
import { getRessetableConfig } from '../../fixtures/resettable';
import { ethers } from 'hardhat';
import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { Bridge } from '../../typechain-types';
import { HardhatEthersSigner } from '@nomicfoundation/hardhat-ethers/signers';

let bridge: Bridge;
let owner: HardhatEthersSigner;
let admin: HardhatEthersSigner;
let user: HardhatEthersSigner;
let signers: HardhatEthersSigner[];

beforeEach(async () => {
  ({bridge, owner, admin, user, signers} = await loadFixture(getRessetableConfig));
});

describe('Owner', () => {
  it('set during the deploy transaction', async () => {
    expect(await bridge.owner()).to.eq(owner);
  });

  it('can set a signer, NewSigner event emited', async () => {
    const [newSigner] = signers;

    const signerBefore = await bridge.getFunction('signer')();
    expect(signerBefore).to.eq(ethers.ZeroAddress);

    await expect(bridge.setSigner(newSigner))
      .to.emit(bridge, 'NewSigner')
      .withArgs(newSigner.address);

    const signerAfter = await bridge.getFunction('signer')();
    expect(signerAfter).to.eq(newSigner.address);
  });

  it.skip('[TODO] can set new admin', async () => {

  });

  it('can switch maintenance mode, MaintenanceState event emited', async () => {
    let isMaintenance = await bridge.isMaintenanceEnabled();
    expect(isMaintenance).to.be.false;

    await expect(bridge.switchMaintenance(true))
      .to.emit(bridge, 'MaintenanceState')
      .withArgs(true);
    
    isMaintenance = await bridge.isMaintenanceEnabled();
    expect(isMaintenance).to.be.true;

    await expect(bridge.switchMaintenance(false))
      .to.emit(bridge, 'MaintenanceState')
      .withArgs(false);

    isMaintenance = await bridge.isMaintenanceEnabled();
    expect(isMaintenance).to.be.false;  
  });

  it('can set required confirmations', async () => {
    const DEFAULT_REQUIRED_CONFIRMATIONS = 0;
    const NEW_REQUIRED_CONFIRMATIONS = 64;

    const defaultRequiredConfirmations = await bridge.requiredConfirmations();
    expect(defaultRequiredConfirmations).to.eq(DEFAULT_REQUIRED_CONFIRMATIONS);

    await bridge.setRequiredConfirmations(NEW_REQUIRED_CONFIRMATIONS);
    
    const newRequiredConfirmations = await bridge.requiredConfirmations();
    expect(newRequiredConfirmations).to.eq(NEW_REQUIRED_CONFIRMATIONS);
  });

  it('can add new validators', async () => {
    const [validator1, validator2] = signers;

    expect(await bridge.isValidator(validator1)).to.be.false;
    expect(await bridge.isValidator(validator2)).to.be.false;

    await expect(bridge.addValidators([validator1, validator2]))
      .to.emit(bridge, 'NewValidator').withArgs(validator1.address)
      .to.emit(bridge, 'NewValidator').withArgs(validator2.address);

    expect(await bridge.isValidator(validator1)).to.be.true;
    expect(await bridge.isValidator(validator2)).to.be.true;
  });

  it('can add link to another contract', async () => {
    const CHAIN_ID = 11189;
    const randomAddress = ethers.getCreateAddress({from: admin.address, nonce: 2222});

    await bridge.addLink(CHAIN_ID, randomAddress);

    const link = await bridge.links(CHAIN_ID);
    expect(link).to.eq(randomAddress);
  });

  it('can add a pair', async () => {
    const CHAIN_ID = 11189;
    const SOURCE_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 123});
    const DESTINATION_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 124});

    await bridge.addPair(SOURCE_ADDRESS, CHAIN_ID, DESTINATION_ADDRESS);

    const expectedPair = [
      SOURCE_ADDRESS,
      CHAIN_ID,
      DESTINATION_ADDRESS
    ];

    expect(await bridge.hasPair(SOURCE_ADDRESS, CHAIN_ID)).to.be.true;
    expect(await bridge.pairs(0)).to.deep.eq(expectedPair);
    expect(await bridge.isPairDeleted(0)).to.be.false;
  });

  it('can remove pair', async () => {
    const CHAIN_ID = 11189;
    const SOURCE_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 123});
    const DESTINATION_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 124});

    await bridge.addPair(SOURCE_ADDRESS, CHAIN_ID, DESTINATION_ADDRESS);

    const expectedPair = [
      SOURCE_ADDRESS,
      CHAIN_ID,
      DESTINATION_ADDRESS
    ];
    const expectedPairId = 0;
    expect(await bridge.pairs(expectedPairId)).to.deep.eq(expectedPair);

    await bridge.removePair(SOURCE_ADDRESS, CHAIN_ID);
    expect(await bridge.pairs(0)).to.deep.eq(expectedPair);
    expect(await bridge.hasPair(SOURCE_ADDRESS, CHAIN_ID)).to.be.false;
    expect(await bridge.isPairDeleted(expectedPairId)).to.be.true;
  });
});

describe('Admin', () => {
  beforeEach(() => {
    bridge = bridge.connect(admin);
  });

  it('set during the deploy transaction', async () => {
    expect(await bridge.admin()).to.eq(admin);
  });

  it('can set a signer, NewSigner event emited', async () => {
    const [newSigner] = signers;

    const signerBefore = await bridge.getFunction('signer')();
    expect(signerBefore).to.eq(ethers.ZeroAddress);

    await expect(bridge.connect(admin).setSigner(newSigner))
      .to.emit(bridge, 'NewSigner')
      .withArgs(newSigner.address);

    const signerAfter = await bridge.getFunction('signer')();
    expect(signerAfter).to.eq(newSigner.address);
  });

  it.skip('[TODO] cannot set new admin', async () => {});

  it('can switch maintenance mode, MaintenanceState event emited', async () => {
    let isMaintenance = await bridge.isMaintenanceEnabled();
    expect(isMaintenance).to.be.false;

    await expect(bridge.switchMaintenance(true))
      .to.emit(bridge, 'MaintenanceState')
      .withArgs(true);
    
    isMaintenance = await bridge.isMaintenanceEnabled();
    expect(isMaintenance).to.be.true;

    await expect(bridge.switchMaintenance(false))
      .to.emit(bridge, 'MaintenanceState')
      .withArgs(false);

    isMaintenance = await bridge.isMaintenanceEnabled();
    expect(isMaintenance).to.be.false;  
  });

  it('can set required confirmations', async () => {
    const DEFAULT_REQUIRED_CONFIRMATIONS = 0;
    const NEW_REQUIRED_CONFIRMATIONS = 64;

    const defaultRequiredConfirmations = await bridge.requiredConfirmations();
    expect(defaultRequiredConfirmations).to.eq(DEFAULT_REQUIRED_CONFIRMATIONS);

    await bridge.setRequiredConfirmations(NEW_REQUIRED_CONFIRMATIONS);
    
    const newRequiredConfirmations = await bridge.requiredConfirmations();
    expect(newRequiredConfirmations).to.eq(NEW_REQUIRED_CONFIRMATIONS);
  });

  it('can add new validators', async () => {
    const [validator1, validator2] = signers;

    expect(await bridge.isValidator(validator1)).to.be.false;
    expect(await bridge.isValidator(validator2)).to.be.false;

    await expect(bridge.addValidators([validator1, validator2]))
      .to.emit(bridge, 'NewValidator').withArgs(validator1.address)
      .to.emit(bridge, 'NewValidator').withArgs(validator2.address);

    expect(await bridge.isValidator(validator1)).to.be.true;
    expect(await bridge.isValidator(validator2)).to.be.true;

    // validator has id
    expect(await bridge.validatorIds(validator1)).to.eq(1);
    expect(await bridge.validatorIds(validator2)).to.eq(2);
  });

  it('cannot add one account as a validator twice', async () => {
    const [validator] = signers;

    // cannot add at once
    await expect(bridge.addValidators([validator, validator]))
      .revertedWith('bridge: validator already exists');

    await expect(bridge.addValidators([validator]))
      .to.emit(bridge, 'NewValidator').withArgs(validator.address);

    // cannot add in separate tx
    await expect(bridge.addValidators([validator]))
      .revertedWith('bridge: validator already exists');
  });

  it('can add link to another contract', async () => {
    const CHAIN_ID = 11189;
    const randomAddress = ethers.getCreateAddress({from: admin.address, nonce: 2222});

    await bridge.addLink(CHAIN_ID, randomAddress);
    // TODO This API is not very user friendly
    const link = await bridge.links(CHAIN_ID);
    expect(link).to.eq(randomAddress);
  });

  it('cannot link a contract twice', async () => {
    const CHAIN_ID = 11189;
    const randomAddress = ethers.getCreateAddress({from: admin.address, nonce: 2222});

    await bridge.addLink(CHAIN_ID, randomAddress);
    await expect(bridge.addLink(CHAIN_ID, randomAddress))
      .revertedWith('bridge: link for this contract already set');
  });

  it('can add a pair', async () => {
    const CHAIN_ID = 11189;
    const SOURCE_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 123});
    const DESTINATION_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 124});

    await bridge.addPair(SOURCE_ADDRESS, CHAIN_ID, DESTINATION_ADDRESS);

    const expectedPair = [
      SOURCE_ADDRESS,
      CHAIN_ID,
      DESTINATION_ADDRESS
    ];

    expect(await bridge.hasPair(SOURCE_ADDRESS, CHAIN_ID)).to.be.true;
    expect(await bridge.pairs(0)).to.deep.eq(expectedPair);
    expect(await bridge.isPairDeleted(0)).to.be.false;
    expect(await bridge.getDestinationAddress(SOURCE_ADDRESS, CHAIN_ID)).to.eq(DESTINATION_ADDRESS);
  });

  it('cannot add one pair twice', async () => {
    const CHAIN_ID = 11189;
    const SOURCE_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 123});
    const DESTINATION_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 124});

    await bridge.addPair(SOURCE_ADDRESS, CHAIN_ID, DESTINATION_ADDRESS);
    await expect(bridge.addPair(SOURCE_ADDRESS, CHAIN_ID, DESTINATION_ADDRESS))
      .revertedWith('bridge: pair already exists');
  });


  it('can remove pair', async () => {
    const CHAIN_ID = 11189;
    const SOURCE_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 123});
    const DESTINATION_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 124});

    await bridge.addPair(SOURCE_ADDRESS, CHAIN_ID, DESTINATION_ADDRESS);

    const expectedPair = [
      SOURCE_ADDRESS,
      CHAIN_ID,
      DESTINATION_ADDRESS
    ];
    const expectedPairId = 0;
    expect(await bridge.pairs(expectedPairId)).to.deep.eq(expectedPair);

    await bridge.removePair(SOURCE_ADDRESS, CHAIN_ID);
    expect(await bridge.pairs(0)).to.deep.eq(expectedPair);
    expect(await bridge.hasPair(SOURCE_ADDRESS, CHAIN_ID)).to.be.false;
    expect(await bridge.isPairDeleted(expectedPairId)).to.be.true;
  });

  it('cannot remove non-registered pair', async () => {
    const CHAIN_ID = 11189;
    const SOURCE_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 123});

    await expect(bridge.removePair(SOURCE_ADDRESS, CHAIN_ID))
      .revertedWith('bridge: invalid pair');
  });
});

describe('Non-admin', () => {
  beforeEach(async () => {
    bridge = bridge.connect(user);
  });

  it('cannot set a signer', async () => {
    const [newSigner] = signers;

    await expect(bridge.setSigner(newSigner))
      .to.revertedWithoutReason();
  });

  it('cannot switch maintenance mode', async () => {
    await expect(bridge.switchMaintenance(true))
      .to.revertedWithoutReason();
  });

  it('cannot set required confirmations', async () => {
    const NEW_REQUIRED_CONFIRMATIONS = 64;

    await expect(bridge.setRequiredConfirmations(NEW_REQUIRED_CONFIRMATIONS))
      .revertedWithoutReason();
  });

  it('cannot add new validators', async () => {
    expect(await bridge.isValidator(user)).to.be.false;

    await expect(bridge.addValidators([user]))
      .revertedWithoutReason();
  });

  it('cannot add link to another contract', async () => {
    const CHAIN_ID = 11189;
    const randomAddress = ethers.getCreateAddress({from: admin.address, nonce: 2222});

    await expect(bridge.addLink(CHAIN_ID, randomAddress))
      .revertedWithoutReason();
  });

  it('cannot add pair', async () => {
    const CHAIN_ID = 11189;
    const SOURCE_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 123});
    const DESTINATION_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 124});

    await expect(bridge.addPair(SOURCE_ADDRESS, CHAIN_ID, DESTINATION_ADDRESS))
      .revertedWithoutReason();
  });

  it('cannot remove pair', async () => {
    const CHAIN_ID = 11189;
    const SOURCE_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 123});
    const DESTINATION_ADDRESS = ethers.getCreateAddress({from: owner.address, nonce: 124});

    await bridge.connect(admin).addPair(SOURCE_ADDRESS, CHAIN_ID, DESTINATION_ADDRESS);

    const expectedPair = [
      SOURCE_ADDRESS,
      CHAIN_ID,
      DESTINATION_ADDRESS
    ];
    const expectedPairId = 0;
    expect(await bridge.pairs(expectedPairId)).to.deep.eq(expectedPair);

    await expect(bridge.removePair(SOURCE_ADDRESS, CHAIN_ID))
      .revertedWithoutReason();
  });
});