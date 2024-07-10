import { ethers } from "hardhat"

export const getRessetableConfig = async () => {
  const [owner, admin, user, ...signers] = await ethers.getSigners();
  const BridgeFactory = await ethers.getContractFactory('Bridge');
  const bridge = await BridgeFactory.deploy(admin);

  return {
    owner,
    admin,
    user,
    signers,
    bridge,
  }
}
