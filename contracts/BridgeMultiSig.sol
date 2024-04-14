// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
	function owner() external view returns (address);
	function balanceOf(address account) external view returns (uint256);

	function mintTo(address account, uint256 amount) external;
	function burnFrom(address account, uint256 amount) external;
}

library TransferHelper {
	function safeTransfer(address token, address to, uint value) internal {
		(bool success, bytes memory data) = token.call(abi.encodeWithSelector(0xa9059cbb, to, value));
		require(success && (data.length == 0 || abi.decode(data, (bool))), 'TransferHelper: TRANSFER_FAILED');
	}

	function safeTransferFrom(address token, address from, address to, uint value) internal {
		(bool success, bytes memory data) = token.call(abi.encodeWithSelector(0x23b872dd, from, to, value));
		require(success && (data.length == 0 || abi.decode(data, (bool))), 'TransferHelper: TRANSFER_FROM_FAILED');
	}

	function safeTransferETH(address to, uint value) internal {
		(bool success,) = to.call{value:value}(new bytes(0));
		require(success, 'TransferHelper: ETH_TRANSFER_FAILED');
	}
}

contract Bridge {
	event Deposit(address indexed token, address indexed from, uint amount, uint targetChain);
	event Transfer(bytes32 indexed txId, uint amount);

	event NewSigner(address indexed signer);
	event NewValidator(address indexed signer);
	event RemovedValidator(address indexed signer);

	struct ConfirmationData {
		uint256 confirmed;
		mapping(address=>bool) confirmedBy;
		bool isSent;
	}

	address public immutable owner;
	address public immutable admin;
	address public signer;

	mapping(address=>bool) public isValidator;
	mapping(bytes32=>ConfirmationData) public confirmations;
	uint32 public requiredConfirmations;

	mapping(address=>bool) public isPeggingToken;
	mapping(address=>bool) public isToken;

	constructor(address _admin) {
		owner = msg.sender;
		admin = _admin;
	}

	modifier onlyOwner() {
		require(msg.sender == owner);
		_;
	}
	
	modifier onlyAdmin() {
		require(msg.sender == admin || msg.sender == owner);
		_;
	}

	modifier onlySigner() {
		require(msg.sender == signer);
		_;
	}

	modifier onlyValidator() {
		require(isValidator[msg.sender] == true);
		_;
	}

	receive() external payable {}

	function setSigner(address _signer) external onlyAdmin {
		signer = _signer;
		emit NewSigner(_signer);
	}

	function setRequiredConfirmations(uint32 _confirmations) external onlyAdmin {
		requiredConfirmations = _confirmations;
	}

	function addValidators(address[] memory _validators) external onlyAdmin {
		for(uint i = 0; i < _validators.length; i++) {
			isValidator[_validators[i]] = true;
			emit NewValidator(_validators[i]);
		}
	}

	function removeValidators(address[] memory _validators) external onlyAdmin {
		for(uint i = 0; i < _validators.length; i++) {
			if(isValidator[_validators[i]]) {
				isValidator[_validators[i]] = false;
				emit RemovedValidator(_validators[i]);
			}
		}
	}

	function confirm(bytes32[] memory _txHashes) external onlyValidator {
		for(uint i = 0; i < _txHashes.length; i++) {
			require(!confirmations[_txHashes[i]].confirmedBy[msg.sender], "bridge: key already confirmed");
			require(!confirmations[_txHashes[i]].isSent, "bridge: txHash already sent");
		}

		for(uint i = 0; i < _txHashes.length; i++) {
			confirmations[_txHashes[i]].confirmedBy[msg.sender] = true;
			confirmations[_txHashes[i]].confirmed++;
		}
	}

	function addTokens(address[] memory tokens) external onlyAdmin {
		for (uint k=0; k<tokens.length; k++) {
			if (IERC20(tokens[k]).owner()==address(this)) {
				isPeggingToken[tokens[k]] = true;
			} else {
				isToken[tokens[k]] = true;
			}
		}
	}

	function deposit(address target, address token, uint amount, uint targetChain) external payable {
		require(msg.sender.code.length==0, "bridge: only personal");
		require(msg.sender!=address(0) && target!=address(0), "bridge: zero sender");
		if (token==address(0)) {
			require(msg.value==amount, "bridge: amount");
		} else {
			if (isPeggingToken[token]) {
				IERC20(token).burnFrom(msg.sender, amount);
			} else if (isToken[token]){
				TransferHelper.safeTransferFrom(token, msg.sender, address(this), amount);
			} else {
				revert();
			}
		}
		emit Deposit(token, target, amount, targetChain);
	}

	function transfer(uint[][] memory args) external payable onlySigner {
		for(uint i=0; i<args.length; i++) {
			address _token 		= address(uint160(args[i][0]));
			address _to			= address(uint160(args[i][1]));
			uint _amount 		= args[i][2];
			bytes32 _txHash = bytes32(args[i][3]);
			if (!confirmations[_txHash].isSent && confirmations[_txHash].confirmed >= requiredConfirmations) {
				if (_token==address(0)) {
					TransferHelper.safeTransferETH(_to, _amount);
				} else {
					if (isPeggingToken[_token]) {
						IERC20(_token).mintTo(_to, _amount);
					} else if (isToken[_token]) {
						TransferHelper.safeTransfer(_token, _to, _amount);
					}
				}
				confirmations[_txHash].isSent = true;
				emit Transfer(_txHash, _amount);
			}
		}
	}
}