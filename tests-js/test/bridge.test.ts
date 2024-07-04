import {ethers} from "hardhat";
import config from "../config";
import { Wallet } from "ethers";
import { ERC20__factory } from "../typechain-types";

it("can connect and do something", async () => {
  const redNetwork = new ethers.JsonRpcProvider(config.redefi.url);
  const ethNetwork = new ethers.JsonRpcProvider(config.ethereum.url);
  
  const signerRed = new Wallet(config.redefi.signerKey).connect(redNetwork);
  const signerEth = new Wallet(config.ethereum.signerKey).connect(ethNetwork);


  const baxRed = ERC20__factory.connect(config.redefi.bax).connect(redNetwork);
  const baxEth = ERC20__factory.connect(config.ethereum.bax).connect(ethNetwork);

  const balanceNativeRed = await redNetwork.getBalance(signerRed);
  const balanceNativeEth = await redNetwork.getBalance(signerEth);

  const balanceBaxRed = await baxRed.balanceOf(signerRed);
  const balanceBaxEth = await baxEth.balanceOf(signerEth);

  const totalSupplyBaxRed = await baxRed.totalSupply();
  const totalSupplyBaxEth = await baxEth.totalSupply();

  console.log("ReDeFi Bax balance:", balanceBaxRed);
  console.log("Ehtereum Bax balance:", balanceBaxEth);

  console.log("ReDeFi signer:", signerRed.address);
  console.log("Ethereum signer:", signerEth.address);

  console.log("Balance on ReDeFi", balanceNativeRed);
  console.log("Balance on Ethereum", balanceNativeEth);
});