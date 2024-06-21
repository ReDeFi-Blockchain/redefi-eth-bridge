import { HardhatUserConfig } from "hardhat/config";
import '@typechain/hardhat';
import '@nomicfoundation/hardhat-ethers';
import '@nomicfoundation/hardhat-chai-matchers';


const config: HardhatUserConfig = {
  solidity: "0.8.24",
  paths: {
    root: "../",
    sources: "./contracts",
    cache: "./tests-js/cache",
    artifacts: "./tests-js/artifacts",
    tests: "./tests-js/test"
  },
  typechain: {
    outDir: "./tests-js/typechain-types"
  }
};

export default config;
