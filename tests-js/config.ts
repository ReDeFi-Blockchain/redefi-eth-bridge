import state from '../testnet/state.json';

const getConfig = () => {
  // TODO: hardcoded for now until configuration becomes necessary
  const redefiUrl = "http://localhost:18545";
  const ethereumUrl = "http://localhost:28545";
  const ganachePrivateKey = "0x4c0883a69102937d6231471b5dbb6204fe512961708279d7d9d1e6b5b9456d11";

  return {
    redefi: {
      url: redefiUrl,
      signerKey: state.relay.signer,
      bax: state.relay.bax
    },
    ethereum: {
      url: ethereumUrl,
      signerKey: ganachePrivateKey,
      bax: state.eth.bax
    }
  } as const;
}

export default getConfig();
