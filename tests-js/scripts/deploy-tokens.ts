import hre, { artifacts, ethers } from 'hardhat';
import { HDNodeWallet, Wallet } from 'ethers';
import config from '../config';

export const deployTokens = async () => {
  const redNetwork = new ethers.JsonRpcProvider(config.redefi.url);
  const ethNetwork = new ethers.JsonRpcProvider(config.ethereum.url);

  const signerRed = HDNodeWallet.fromSeed(config.redefi.signerKey).connect(redNetwork);
  const signerEth = new Wallet(config.ethereum.signerKey).connect(ethNetwork);

  const balanceNativeRed = await redNetwork.getBalance(signerRed);
  const balanceNativeEth = await redNetwork.getBalance(signerEth);

  console.log(`Red signer | ${signerRed.address} | Balance ${balanceNativeRed / (10n ** 18n)}`)
  console.log(`Eth signer | ${signerEth.address} | Balance ${balanceNativeEth / (10n ** 18n)}`)

  const factory = await ethers.getContractFactoryFromArtifact(RedArtifacts, signerRed);

  const contract = await factory.connect(signerRed).deploy();
  const redBax = REDToken__factory.connect(await contract.getAddress()).connect(redNetwork);
  console.log(await redBax.name());
}

deployTokens().catch(e => {
  console.error("CANNOT DEPLOY TOKENS");
  throw e;
})