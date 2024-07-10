import { JsonRpcProvider, Wallet } from "ethers";
import { ethers } from "hardhat";
import { Bridge, TestERC20 } from "../typechain-types";

let config: Config;

export const getPersistentConfig = async (): Promise<Config> => {
  // TODO get from envs:
  const rpcRed = "http://localhost:3005";
  const rpcEth = "http://localhost:3006";
  const hhPrivateKeys = [
    '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
    '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d',
    '0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a',
    '0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6',
    '0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a',
  ];

  // 1. providers
  const providerRed = new ethers.JsonRpcProvider(rpcRed);
  const providerEth = new ethers.JsonRpcProvider(rpcEth);

  // 2. signers
  const [ownerRed, adminRed, ...otherRed] = hhPrivateKeys.map(pk => new ethers.Wallet(pk, providerRed));
  const [ownerEth, adminEth, ...otherEth] = hhPrivateKeys.map(pk => new ethers.Wallet(pk, providerEth));

  // 3. bridges
  const BridgeFactory = await ethers.getContractFactory('Bridge');
  const bridgeRed = await BridgeFactory.connect(ownerRed).deploy(adminRed);
  const bridgeEth = await BridgeFactory.connect(ownerEth).deploy(adminEth);
  await Promise.all([
    bridgeRed.waitForDeployment(), bridgeEth.waitForDeployment()
  ]);

  const ERC20Factory = await ethers.getContractFactory('TestERC20');
  const redRed = await ERC20Factory.connect(ownerRed).deploy();
  const redEth = await ERC20Factory.connect(ownerEth).deploy();
  await Promise.all([
    redRed.waitForDeployment(), redEth.waitForDeployment()
  ]);

  config = {
    red: {
      provider: providerRed,
      owner: ownerRed,
      admin: adminRed,
      signers: otherRed,
      bridge: bridgeRed,
      red: redRed,
    },
    eth: {
      provider: providerEth,
      owner: ownerEth,
      admin: adminEth,
      signers: otherEth,
      bridge: bridgeEth,
      red: redEth
    }
  };

  return config;
};

export type ChainConfig = {
  provider: JsonRpcProvider,
  owner: Wallet,
  admin: Wallet,
  signers: Wallet[],
  bridge: Bridge,
  red: TestERC20
}

export interface Config {
  red: ChainConfig,
  eth: ChainConfig,
}