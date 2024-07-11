import { ethers } from "hardhat"

export const getRessetableConfig = async () => {
  const [owner, admin, user, ...signers] = await ethers.getSigners();
  const BridgeFactory = await ethers.getContractFactory('Bridge');
  const bridge = await BridgeFactory.deploy(admin);

  const ERC20Factory = await ethers.getContractFactory('TestERC20');
  const token1 = await ERC20Factory.deploy();
  const token2 = await ERC20Factory.deploy();
  const token3 = await ERC20Factory.deploy();

  return {
    owner,
    admin,
    user,
    signers,
    tokens: [token1, token2, token3],
    bridge,
  }
}
