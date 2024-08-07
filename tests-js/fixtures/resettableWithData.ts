import { loadFixture } from "@nomicfoundation/hardhat-network-helpers";
import { getRessetableConfig } from "./resettable";
import { ethers } from "hardhat";
import { TestERC20, TestERC20__factory } from "../typechain-types";

type Bignumberish = bigint | number;

export interface ListInfo {
  amount: bigint,
  hash: string,
  chainId: number,
  recepient: string,
  token: TestERC20,
  data: Bignumberish[]
}


export const getRessetableWithDataConfig = async () => {
  const bridgeBalance = 100n * (10n ** 18n);
  const {owner, admin, user, signers, tokens, bridge,
  } = await loadFixture(getRessetableConfig);

  const [ownedToken, nonOwnedToken, nonRegisteredToken] = tokens;
  await bridge.registerTokens([ownedToken, nonOwnedToken, ethers.ZeroAddress]);
  await bridge.changeTokenOwnership(ownedToken, true);

  // set bridge as admin
  await ownedToken.connect(owner).setAdmin(bridge);
  await nonOwnedToken.connect(owner).setAdmin(bridge);


  // topup bridge balance
  await ownedToken.connect(owner).transfer(await bridge.getAddress(), bridgeBalance);
  await nonOwnedToken.connect(owner).transfer(await bridge.getAddress(), bridgeBalance);
  await bridge.addFunds(ethers.ZeroAddress, bridgeBalance, {value: bridgeBalance});

  const [user2, signer, validator] = signers;
  // NOTICE: if change signer account also change admin in TestERC20.sol
  await bridge.setSigner(signer);
  await bridge.addValidators([validator]);

  const amount1 = 100n * (10n ** 18n);
  const sourceChain1 = 1899;
  const txHash1 = '0x90434dda53a751ae504ae030c79d7342dbebe941a00958a646cf126c6b4f71f0';
  const tokenAddress1 = await ownedToken.getAddress();
  
  const amount2 = 50n * (10n ** 18n);
  const sourceChain2 = 44444;
  const txHash2 = '0xecb5c281698ea4756394cbd0e0d7a09ca03d71ed52ceda6065a4eeb58731c596';
  const tokenAddress2 = await nonOwnedToken.getAddress();

  const amount3 = 75n * (10n ** 18n);
  const sourceChain3 = 55555;
  const txHash3 = '0xd5fb7341224c07f4d643b1e0724c3d26c3d786be56dcbf255785bf3970f08231';
  const tokenAddress3 = ethers.ZeroAddress;

  const bridgeOnSiblingChain = ethers.getCreateAddress({from: admin.address, nonce: 12345});
  await bridge.addLink(sourceChain1, bridgeOnSiblingChain);
  await bridge.addLink(sourceChain2, bridgeOnSiblingChain);
  await bridge.addLink(sourceChain3, bridgeOnSiblingChain);

  const VALID_LIST_INFO_1: ListInfo = {
    amount: amount1,
    hash: txHash1,
    chainId: sourceChain1,
    recepient: user.address,
    token: ownedToken,
    data: [
      BigInt(tokenAddress1),
      BigInt(user.address),
      amount1,
      sourceChain1,
      BigInt(txHash1),
    ]
  };

  const VALID_LIST_INFO_2: ListInfo = {
    amount: amount2,
    hash: txHash2,
    chainId: sourceChain2,
    recepient: user2.address,
    token: nonOwnedToken,
    data: [
      BigInt(tokenAddress2),
      BigInt(user2.address),
      amount2,
      sourceChain2,
      BigInt(txHash2),
    ]
  };

  const VALID_LIST_INFO_3: ListInfo = {
    amount: amount3,
    hash: txHash3,
    chainId: sourceChain3,
    recepient: admin.address,
    token: TestERC20__factory.connect(tokenAddress3, ethers.provider),
    data: [
      BigInt(tokenAddress3),
      BigInt(admin.address),
      amount3,
      sourceChain3,
      BigInt(txHash3),
    ]
  };

  return {
    owner,
    admin,
    users: [user, user2],
    signer,
    validator,
    tokens: {
      owned: ownedToken,
      nonOwned: nonOwnedToken,
      nonRegistered: nonRegisteredToken,
    },
    bridge,
    data: [
       VALID_LIST_INFO_1,
       VALID_LIST_INFO_2,
       VALID_LIST_INFO_3
    ]
  }
}
