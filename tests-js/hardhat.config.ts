import * as dotenv from "dotenv";
dotenv.config();
import { HardhatUserConfig } from "hardhat/config";
import '@typechain/hardhat';
import "@nomicfoundation/hardhat-ethers";
import "@nomicfoundation/hardhat-chai-matchers";
import "@nomicfoundation/hardhat-ignition-ethers";
import 'solidity-coverage';

const {ALCHEMY_SEPOLIA_KEY, SEPOLIA_PRIVATE_KEY} = process.env;

const config: HardhatUserConfig = {
  solidity: {
    compilers: [
      {
        version: "0.8.24",
      },
      {
        version: "0.8.20"
      }
    ],
    overrides: {
      "contracts/REDToken.sol": {
        version: "0.8.20"
      }
    }
  },
  networks: {
    hardhat: {},
    sepolia: {
      url: `https://eth-sepolia.g.alchemy.com/v2/${ALCHEMY_SEPOLIA_KEY}`,
      accounts: [SEPOLIA_PRIVATE_KEY!],
    },
  },
  typechain: {
  },
  mocha: {
    timeout: 180000
  },
};

export default config;
