REPO_URL=https://github.com/ReDeFi-Blockchain/redefi-red-contract
DIR_NAME_TESTS_JS=./tests-js
DIR_NAME_TESTNET=./testnet
DIR_NAME_RED=./tests-js/contracts/redefi-red-contract
SECRETS_FILE=$(DIR_NAME_RED)/secrets.ts

spinup-once:
	python launch_on_testnet.py && \
	cd $(DIR_NAME_TESTNET) && \
	docker compose up -d

clone-red:
	git clone $(REPO_URL) $(DIR_NAME_RED)

remove-red:
	rm -rf $(DIR_NAME_RED)

install-red:
	cd $(DIR_NAME_RED) && npm install

# add non-real private keys to make compiler happy
create-secrets:
	echo "export const secrets = { privateKeys: ['0xa28ecc3eaee76a53984ca8c35709e9fe66242148bfd24842f08168d6e7e77bf2','0xa28ecc3eaee76a53984ca8c35709e9fe66242148bfd24842f08168d6e7e77bf2','0xa28ecc3eaee76a53984ca8c35709e9fe66242148bfd24842f08168d6e7e77bf2'] };" > $(SECRETS_FILE)

compile:
	cd $(DIR_NAME_TESTS_JS) && npx hardhat compile

compile-red:
	cd $(DIR_NAME_RED) && npx hardhat compile

spinup:
	$(MAKE) spinup-once
	$(MAKE) spinup-once

hh: remove-red clone-red install-red create-secrets compile-red

.PHONY: clone-red remove-red install-red create-secrets compile-red spinup spinup-once hh
