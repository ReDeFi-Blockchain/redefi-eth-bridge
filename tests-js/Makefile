all: copy-bridge compile

copy-bridge:
	@if [ -e ./contracts/BridgeLinked.sol ]; then rm ./contracts/BridgeLinked.sol; fi
	cp ../contracts/BridgeLinked.sol ./contracts/BridgeLinked.sol

compile:
	npx hardhat compile --force

chains:
	npx hardhat node --port 3005 & \
	npx hardhat node --port 3006

.PHONY: copy-bridge compile
