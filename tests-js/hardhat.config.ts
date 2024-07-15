import { HardhatUserConfig } from "hardhat/config";
import '@typechain/hardhat';
import "@nomicfoundation/hardhat-ethers";
import "@nomicfoundation/hardhat-chai-matchers";
import 'solidity-coverage';

const config: HardhatUserConfig = {
  solidity: "0.8.24",
  typechain: {
  },
  mocha: {
    timeout: 180000
  }
};

export default config;
