all: copy-bridge compile

copy-bridge:
	@if [ -e ./contracts/BridgeLinked.sol ]; then rm ./contracts/BridgeLinked.sol; fi
	cp ../contracts/BridgeLinked.sol ./contracts/BridgeLinked.sol

copy-red:
	@if [ -e ./contracts/REDToken.sol ]; then rm ./contracts/REDToken.sol; fi
	wget https://raw.githubusercontent.com/ReDeFi-Blockchain/redefi-red-contract/master/contracts/REDToken.sol -O ./contracts/REDToken.sol

compile:
	npx hardhat compile --force

chains:
	npx hardhat node --port 3005 & \
	npx hardhat node --port 3006

.PHONY: copy-bridge compile
