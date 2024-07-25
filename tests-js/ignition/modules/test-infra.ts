import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";
import { ethers } from "hardhat";

export default buildModule("Testinfra", (m) => {
  const {ADMIN} = process.env;
  if (!ADMIN) throw Error('You have to set `ADMIN` env');
  if (!ADMIN.startsWith('0x')) throw Error("Admin is not eth address");

  // Deploying contracts
  const red = m.contract("REDToken");
  const bax = m.contract("BAXToken");
  const bridge = m.contract("Bridge", [ADMIN]);

  // Providing funds to the bridge
  const ADD_FUNDS = 10000n * (10n ** 18n);
  m.call(red, "approve", [bridge, ADD_FUNDS]);
  m.call(bax, "approve", [bridge, ADD_FUNDS]);

  m.call(bridge, "addFunds", [red, ADD_FUNDS]);
  m.call(bridge, "addFunds", [bax, ADD_FUNDS]);

  // Register validators
  const validator1 = ethers.Wallet.createRandom();
  const validator2 = ethers.Wallet.createRandom();
  const validator3 = ethers.Wallet.createRandom();

  console.log("ADMIN");
  console.log(ADMIN);

  console.log("VALIDATORS:");
  console.log(validator1.address, validator1.privateKey);
  console.log(validator2.address, validator2.privateKey);
  console.log(validator3.address, validator3.privateKey);

  // Register signer
  const signer = ethers.Wallet.createRandom();
  console.log("SIGNER:");
  console.log(signer.address, signer.privateKey);


  m.call(bridge, "addValidators", [
    [
      validator1.address,
      validator2.address,
      validator3.address
    ],
  ]);

  m.call(bridge, "setSigner", [signer.address]);

  // Register tokens
  m.call(bridge, "registerTokens", [[red, bax]])

  return { red, bax, bridge };
});
