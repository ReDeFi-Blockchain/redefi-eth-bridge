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
	event Deposit(address indexed token, address indexed receiver, uint amount, uint targetChain);
	event Transfer(bytes32 indexed txId, uint amount);

	event NewSigner(address indexed signer);
	event NewValidator(address indexed signer);
	event RemovedValidator(address indexed signer);

	struct ConfirmationData {
		address token;
		address receiver;
		uint256 amount;
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
			require(confirmations[_txHashes[i]].amount > 0, "bridge: unknown txHash");
			require(!confirmations[_txHashes[i]].confirmedBy[msg.sender], "bridge: txHash already confirmed");
			require(!confirmations[_txHashes[i]].isSent, "bridge: txHash already sent");
		}

		for(uint i = 0; i < _txHashes.length; i++) {
			confirmations[_txHashes[i]].confirmedBy[msg.sender] = true;
			confirmations[_txHashes[i]].confirmed++;
		}
	}

	function addTokens(address[] memory _tokens) external onlyAdmin {
		for (uint k=0; k< _tokens.length; k++) {
			if (IERC20(_tokens[k]).owner() == address(this)) {
				isPeggingToken[_tokens[k]] = true;
			} else {
				isToken[_tokens[k]] = true;
			}
		}
	}

	function deposit(address _receiver, address _token, uint _amount, uint _targetChain) external payable {
		require(msg.sender.code.length == 0, "bridge: only personal");
		require(msg.sender != address(0) && _receiver != address(0), "bridge: zero receiver");
		if (_token == address(0)) {
			require(msg.value == _amount, "bridge: amount");
		} else {
			if (isPeggingToken[_token]) {
				IERC20(_token).burnFrom(msg.sender, _amount);
			} else if (isToken[_token]){
				TransferHelper.safeTransferFrom(_token, msg.sender, address(this), _amount);
			} else {
				revert();
			}
		}
		emit Deposit(_token, _receiver, _amount, _targetChain);
	}

	function list(uint[][] memory _args) external onlySigner {
		for(uint i = 0; i < _args.length; i++) {
			address _token = address(uint160(_args[i][0]));
			address _to = address(uint160(_args[i][1]));
			uint _amount = _args[i][2];
			bytes32 _txHash = bytes32(_args[i][3]);
			require(_amount > 0, "bridge: amount must be more than zero");
			require(confirmations[_txHash].amount == 0, "bridge: txHash already listed");
			confirmations[_txHash].token = _token;
			confirmations[_txHash].receiver = _to;
			confirmations[_txHash].amount = _amount;
		}
	}

	function transfer(bytes32[] memory _txHashes) external payable onlySigner {
		for(uint i = 0; i < _txHashes.length; i++) {
			bytes32 _txHash = _txHashes[i];
			if (!confirmations[_txHash].isSent && confirmations[_txHash].confirmed >= requiredConfirmations) {
				address _token = confirmations[_txHash].token;
				address _to = confirmations[_txHash].receiver;
				uint256 _amount = confirmations[_txHash].amount;
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