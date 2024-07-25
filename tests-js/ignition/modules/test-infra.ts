import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";
import { ethers } from "hardhat";

export default buildModule("Testinfra", (m) => {
  const {ADMIN} = process.env;
  if (!ADMIN) throw Error('You have to set `ADMIN` env');
  if (!ADMIN.startsWith('0x')) throw Error("Admin is not eth address");

  const red = m.contract("REDToken");
  const bax = m.contract("BAXToken");
  const bridge = m.contract("Bridge", [ADMIN]);

  const validator1 = ethers.Wallet.createRandom();
  const validator2 = ethers.Wallet.createRandom();
  const validator3 = ethers.Wallet.createRandom();

  console.log("ADMIN");
  console.log(ADMIN);

  console.log("VALIDATORS:");
  console.log(validator1.address, validator1.privateKey);
  console.log(validator2.address, validator2.privateKey);
  console.log(validator3.address, validator3.privateKey);

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

  m.call(bridge, "registerTokens", [[red, bax]])

  452040525290470781
  138365736361440903
  50105362756951939

  return { red, bax, bridge };
});
