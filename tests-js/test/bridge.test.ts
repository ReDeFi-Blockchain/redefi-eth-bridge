import {ethers} from "hardhat";
import config from "../config";
import { Wallet } from "ethers";
import { IERC20__factory } from "../typechain-types";

it("can connect and do something", async () => {
  const redefi = new ethers.JsonRpcProvider(config.redefi.url);
  const ethereum = new ethers.JsonRpcProvider(config.ethereum.url);
  
  const signerRedefi = new Wallet(config.redefi.signerKey).connect(redefi);
  const signerEthereum = new Wallet(config.ethereum.signerKey).connect(ethereum);

  const baxRedefi = IERC20__factory.connect(config.redefi.bax).connect(redefi);
  const baxEthereum = IERC20__factory.connect(config.ethereum.bax).connect(ethereum);

  const balanceRedefi = await redefi.getBalance(signerRedefi);
  const balanceEthereum = await redefi.getBalance(signerEthereum);

  const baxBalanceRedefi = await baxRedefi.balanceOf(signerRedefi);
  const baxBalanceEthereum = await baxEthereum.balanceOf(signerEthereum);

  console.log("ReDeFi Bax balance:", baxBalanceRedefi);
  console.log("Ehtereum Bax balance:", baxBalanceEthereum);

  console.log("ReDeFi signer:", signerRedefi.address);
  console.log("Ethereum signer:", signerEthereum.address);

  console.log("Balance on ReDeFi", balanceRedefi);
  console.log("Balance on Ethereum", balanceEthereum);
});