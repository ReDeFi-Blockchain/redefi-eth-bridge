import { JsonRpcProvider, Wallet } from "ethers";
import { ethers } from "hardhat";
import { Bridge, TestERC20, TestERC20__factory } from "./typechain-types";

let config: Config;

export const getConfig = async (): Promise<Config> => {
  if (config) return config;
  
  // TODO get from envs:
  const rpcRed = "http://localhost:3005";
  const rpcEth = "http://localhost:3006";
  const signerKey = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"

  // 1. providers
  const providerRed = new ethers.JsonRpcProvider(rpcRed);
  const providerEth = new ethers.JsonRpcProvider(rpcEth);

  // 2. signers
  const signerRed = new ethers.Wallet(signerKey, providerRed);
  const signerEth = new ethers.Wallet(signerKey, providerEth);

  // 3. bridges
  const BridgeFactory = await ethers.getContractFactory('Bridge');
  const bridgeRed = await BridgeFactory.connect(signerRed).deploy(signerRed); //).connect(providerRed);
  const bridgeEth = await BridgeFactory.connect(signerEth).deploy(signerEth); //).connect(providerEth);

  const ERC20Factory = await ethers.getContractFactory('TestERC20');
  const redRed = await ERC20Factory.connect(signerRed).deploy();
  const redEth = await ERC20Factory.connect(signerEth).deploy();

  config = {
    red: {
      provider: providerRed,
      signer: signerRed,
      bridge: bridgeRed,
      red: redRed,
    },
    eth: {
      provider: providerEth,
      signer: signerEth,
      bridge: bridgeEth,
      red: redEth
    }
  };

  return config;
};

type NetworkConfig = {
  provider: JsonRpcProvider,
  signer: Wallet,
  bridge: Bridge,
  red: TestERC20
}

export interface Config {
  red: NetworkConfig,
  eth: NetworkConfig,
}