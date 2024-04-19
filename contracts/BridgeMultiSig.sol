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
	event Deposit(address indexed token, address indexed receiver, uint amount, uint targetChainId);
	event Transfer(bytes32 indexed txHash, uint amount);

	event NewSigner(address indexed signer);
	event NewValidator(address indexed signer);
	event RemovedValidator(address indexed signer);

	address public immutable owner;
	address public immutable admin;
	address public signer;

	mapping(address => uint16) public validatorIds;
	address[] public validators;
	mapping(address => bool) public isValidatorDeleted;

	struct ConfirmationData {
		bool isSent;
		uint16 confirmed;
		uint16[] confirmedBy;
		uint16 tokenId;
		address receiver;
		uint256 amount;
	}

	mapping(bytes32 => ConfirmationData) public confirmations;
	uint16 public requiredConfirmations;

	struct TokenData {
		uint16 tokenId;
		bool isOwn;
	}

	mapping(address => TokenData) public isToken;
	address[] public tokens;

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
		require(isValidator(msg.sender) && !isValidatorDeleted[msg.sender]);
		_;
	}

	receive() external payable {}

	function setSigner(address _signer) external onlyAdmin {
		signer = _signer;
		emit NewSigner(_signer);
	}

	function setRequiredConfirmations(uint16 _confirmations) external onlyAdmin {
		requiredConfirmations = _confirmations;
	}

	function isValidator(address _validator) public returns (bool) {
		for(uint i = 0; i < validators.length; i++) {
			if(validators[i] == _validator) {
				return true;
			}
		}
		return false;
	}

	function addValidators(address[] memory _validators) external onlyAdmin {
		for(uint i = 0; i < _validators.length; i++) {
			require(validators.length <= type(uint16).max, "bridge: validators count exceeds uint16 range");
			require(!isValidator(_validators[i]), "bridge: validator already exists");
			validators.push(_validators[i]);
			validatorIds[_validators[i]] = uint16(validators.length);
			emit NewValidator(_validators[i]);
		}
	}

	function changeValidatorState(address _validator, bool _isDeleted) external onlyAdmin {
		require(isValidator(_validator), "bridge: unable to change state of unknown validator");
		require(isValidatorDeleted[_validator] != _isDeleted, "bridge: validator state: nothing to change");
		isValidatorDeleted[_validator] = _isDeleted;
		if(_isDeleted) {
			emit RemovedValidator(_validator);
		}
		else {
			emit NewValidator(_validator);
		}
	}

	function isConfirmedBy(bytes32 _txHash, address _validator) public returns (bool) {
		uint16 _validatorId = validatorIds[_validator];
		for(uint i = 0; i < confirmations[_txHash].confirmedBy.length; i++) {
			if(confirmations[_txHash].confirmedBy[i] == _validatorId) return true;
		}
		return false;
	}

	function confirm(bytes32[] memory _txHashes) external onlyValidator {
		for(uint i = 0; i < _txHashes.length; i++) {
			require(confirmations[_txHashes[i]].amount > 0, "bridge: unknown txHash");
			require(!confirmations[_txHashes[i]].isSent, "bridge: txHash already sent");
			require(!isConfirmedBy(_txHashes[i], msg.sender), "bridge: txHash already confirmed");
		}

		for(uint i = 0; i < _txHashes.length; i++) {
			confirmations[_txHashes[i]].confirmedBy.push(validatorIds[msg.sender]);
			confirmations[_txHashes[i]].confirmed++;
		}
	}

	function addTokens(address[] memory _tokens) external onlyAdmin {
		for (uint i = 0; i < _tokens.length; i++) {
			require(tokens.length <= type(uint16).max, "bridge: tokens count exceeds uint16 range");
			require(isToken[_tokens[i]].tokenId < 1, "bridge: token already exists");
			bool _isOwn = IERC20(_tokens[i]).owner() == address(this);
			tokens.push(_tokens[i]);
			isToken[_tokens[i]].isOwn = _isOwn;
			isToken[_tokens[i]].tokenId = uint16(tokens.length);
		}
	}

	function deposit(address _receiver, address _token, uint _amount, uint _targetChainId) external payable {
		require(msg.sender.code.length == 0, "bridge: only personal");
		require(msg.sender != address(0) && _receiver != address(0), "bridge: zero receiver");
		require(isToken[_token].tokenId > 0, "bridge: unable to deposit unregistered token");
		if (_token == address(0)) {
			require(msg.value == _amount, "bridge: invalid amount");
		} else {
			if (isToken[_token].isOwn) {
				IERC20(_token).burnFrom(msg.sender, _amount);
			} else {
				TransferHelper.safeTransferFrom(_token, msg.sender, address(this), _amount);
			}
		}
		emit Deposit(_token, _receiver, _amount, _targetChainId);
	}

	function list(uint[][] memory _args) external onlySigner {
		for(uint i = 0; i < _args.length; i++) {
			address _token = address(uint160(_args[i][0]));
			uint16 _tokenId = isToken[_token].tokenId;
			require(_tokenId > 0, "bridge: trying to list unregistered token");
			address _to = address(uint160(_args[i][1]));
			uint _amount = _args[i][2];
			bytes32 _txHash = bytes32(_args[i][3]);
			require(_amount > 0, "bridge: amount must be more than zero");
			require(confirmations[_txHash].amount == 0, "bridge: txHash already listed");
			confirmations[_txHash].tokenId = _tokenId;
			confirmations[_txHash].receiver = _to;
			confirmations[_txHash].amount = _amount;
		}
	}

	function transfer(bytes32[] memory _txHashes) external payable onlySigner {
		for(uint i = 0; i < _txHashes.length; i++) {
			bytes32 _txHash = _txHashes[i];
			if (!confirmations[_txHash].isSent && confirmations[_txHash].confirmed >= requiredConfirmations) {
				uint16 _tokenId = confirmations[_txHash].tokenId;
				address _token = tokens[_tokenId - 1];
				address _to = confirmations[_txHash].receiver;
				uint256 _amount = confirmations[_txHash].amount;
				if (_token==address(0)) {
					TransferHelper.safeTransferETH(_to, _amount);
				} else {
					if (isToken[_token].isOwn) {
						IERC20(_token).mintTo(_to, _amount);
					} else {
						TransferHelper.safeTransfer(_token, _to, _amount);
					}
				}
				confirmations[_txHash].isSent = true;
				emit Transfer(_txHash, _amount);
			}
		}
	}
}