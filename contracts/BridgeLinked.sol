// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
	function owner() external view returns (address);
	function balanceOf(address account) external view returns (uint256);

	function mint(address account, uint256 amount) external;
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
	event Listed(bytes32 indexed txHash, uint sourceChainId);
	event Confirmed(bytes32 indexed txHash, uint16 validatorId);

	event NewAdmin(address indexed admin);
	event NewSigner(address indexed signer);
	event NewValidator(address indexed validator);
	event RemovedValidator(address indexed validator);
	event MaintenanceState(bool indexed state);

	address public immutable owner;
	address public admin;
	address public signer;
	bool public isMaintenanceEnabled;

	mapping(address => uint16) public validatorIds;
	address[] public validators;
	mapping(address => bool) public isValidatorDeleted;

	mapping(uint => address) public links;
	
	struct PairData {
		address sourceAddress;
		uint destinationChainId;
		address destinationAddress;
	}

	PairData[] public pairs;
	mapping(uint16 => bool) public isPairDeleted;

	struct ConfirmationData {
		address receiver;
		uint256 amount;
		uint16[] confirmedBy;
		uint16 tokenId;
		bool isSent;
	}

	mapping(bytes32 => ConfirmationData) public confirmations;
	uint16 public requiredConfirmations;

	struct TokenData {
		uint16 tokenId;
		bool isOwn;
		mapping(address => uint256) funds;
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
		require(isValidator(msg.sender));
		_;
	}

	modifier onlyWithActiveBridge() {
		require(!isMaintenanceEnabled);
		_;
	}

	receive() external payable {}

	function setAdmin(address _admin) external onlyOwner {
		admin = _admin;
		emit NewAdmin(_admin);
	}

	function switchMaintenance(bool _state) external onlyAdmin {
		isMaintenanceEnabled = _state;
		emit MaintenanceState(_state);
	}

	function setSigner(address _signer) external onlyAdmin {
		signer = _signer;
		emit NewSigner(_signer);
	}

	function setRequiredConfirmations(uint16 _confirmations) external onlyAdmin {
		requiredConfirmations = _confirmations;
	}

	function isValidator(address _validator) public view returns (bool) {
		return validatorIds[_validator] > 0 && !isValidatorDeleted[_validator];
	}

	function addValidators(address[] memory _validators) external onlyAdmin {
		for(uint i = 0; i < _validators.length; i++) {
			require(validators.length <= type(uint16).max, "bridge: validators count exceeds uint16 range");
			require(validatorIds[_validators[i]] < 1, "bridge: validator already exists");
			validators.push(_validators[i]);
			validatorIds[_validators[i]] = uint16(validators.length);
			emit NewValidator(_validators[i]);
		}
	}

	function addLink(uint _chainId, address _contractAddress) external onlyAdmin {
		require(links[_chainId] == address(0), "bridge: link for this contract already set");
		links[_chainId] = _contractAddress;
	}

	function addPair(address _sourceAddress, uint _destinationChainId, address _destinationAddress) external onlyAdmin {
		require(!hasPair(_sourceAddress, _destinationChainId), "bridge: pair already exists");
		pairs.push(PairData(_sourceAddress, _destinationChainId, _destinationAddress));
	}

	function removePair(address _sourceAddress, uint _destinationChainId) external onlyAdmin {
		require(hasPair(_sourceAddress, _destinationChainId), "bridge: invalid pair");
		for(uint i = 0; i < pairs.length; i++) {
			if(pairs[i].sourceAddress == _sourceAddress && pairs[i].destinationChainId == _destinationChainId && !isPairDeleted[uint16(i)]) {
				isPairDeleted[uint16(i)] = true;
			}
		}
	}

	function hasPair(address _sourceAddress, uint _destinationChainId) public view returns (bool) {
		for(uint i = 0; i < pairs.length; i++) {
			if(pairs[i].sourceAddress == _sourceAddress && pairs[i].destinationChainId == _destinationChainId && !isPairDeleted[uint16(i)]) return true;
		}
		return false;
	}

	function getDestinationAddress(address _sourceAddress, uint _destinationChainId) public view returns (address) {
		for(uint i = 0; i < pairs.length; i++) {
			if(pairs[i].sourceAddress == _sourceAddress && pairs[i].destinationChainId == _destinationChainId && !isPairDeleted[uint16(i)]) return pairs[i].destinationAddress;
		}
		return address(0);
	}

	function changeValidatorState(address _validator, bool _isDeleted) external onlyAdmin {
		require(validatorIds[_validator] > 0, "bridge: unable to change state of unknown validator");
		require(isValidatorDeleted[_validator] != _isDeleted, "bridge: validator state: nothing to change");
		isValidatorDeleted[_validator] = _isDeleted;
		if(_isDeleted) {
			emit RemovedValidator(_validator);
		}
		else {
			emit NewValidator(_validator);
		}
	}

	function isConfirmedBy(bytes32 _txHash, address _validator) public view returns (bool) {
		uint16 _validatorId = validatorIds[_validator];
		for(uint i = 0; i < confirmations[_txHash].confirmedBy.length; i++) {
			if(confirmations[_txHash].confirmedBy[i] == _validatorId) return true;
		}
		return false;
	}

	function confirmedBy(bytes32 _txHash) public view returns (uint16[] memory) {
		return confirmations[_txHash].confirmedBy;
	}

	function confirm(bytes32[] memory _txHashes) external onlyValidator {
		for(uint i = 0; i < _txHashes.length; i++) {
			require(confirmations[_txHashes[i]].amount > 0, "bridge: unknown txHash");
			require(!confirmations[_txHashes[i]].isSent, "bridge: txHash already sent");
			require(!isConfirmedBy(_txHashes[i], msg.sender), "bridge: txHash already confirmed");
		}

		for(uint i = 0; i < _txHashes.length; i++) {
			confirmations[_txHashes[i]].confirmedBy.push(validatorIds[msg.sender]);
			emit Confirmed(_txHashes[i], validatorIds[msg.sender]);
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

	function addFunds(address _token, uint256 _amount) external payable onlyWithActiveBridge {
		require(_amount > 0, "bridge: amount must be greater than zero");
		require(isToken[_token].tokenId > 0, "bridge: token should be registered first");
		require(!isToken[_token].isOwn, "bridge: no need any funds for owned tokens");
		if(_token == address(0)) {
			require(msg.value == _amount, "bridge: invalid amount");
		}
		else {
			TransferHelper.safeTransferFrom(_token, msg.sender, address(this), _amount);
		}
		isToken[_token].funds[msg.sender] += _amount;
	}

	function withdrawFunds(address _token, uint256 _amount) external payable {
		require(_amount > 0, "bridge: amount must be greater than zero");
		require(isToken[_token].tokenId > 0, "bridge: token should be registered first");
		require(!isToken[_token].isOwn, "bridge: no need any funds for owned tokens");
		require(isToken[_token].funds[msg.sender] >= _amount, "bridge: invalid amount");
		if(_token == address(0)) {
			TransferHelper.safeTransferETH(msg.sender, _amount);
		}
		else {
			TransferHelper.safeTransfer(_token, msg.sender, _amount);
		}
		isToken[_token].funds[msg.sender] -= _amount;
	}

	function deposit(address _receiver, address _token, uint _amount, uint _targetChainId) external payable onlyWithActiveBridge {
		require(_amount > 0, "bridge: amount must be greater than zero");
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
			uint _sourceChainId = _args[i][3];
			bytes32 _txHash = bytes32(_args[i][4]);
			require(_amount > 0, "bridge: amount must be more than zero");
			require(confirmations[_txHash].amount == 0, "bridge: txHash already listed");
			confirmations[_txHash].tokenId = _tokenId;
			confirmations[_txHash].receiver = _to;
			confirmations[_txHash].amount = _amount;
			emit Listed(_txHash, _sourceChainId);
		}
	}

	function transfer(bytes32[] memory _txHashes) external payable onlySigner {
		for(uint i = 0; i < _txHashes.length; i++) {
			bytes32 _txHash = _txHashes[i];
			if (!confirmations[_txHash].isSent && confirmations[_txHash].confirmedBy.length >= requiredConfirmations) {
				uint16 _tokenId = confirmations[_txHash].tokenId;
				address _token = tokens[_tokenId - 1];
				address _to = confirmations[_txHash].receiver;
				uint256 _amount = confirmations[_txHash].amount;
				if (_token==address(0)) {
					TransferHelper.safeTransferETH(_to, _amount);
				} else {
					if (isToken[_token].isOwn) {
						IERC20(_token).mint(_to, _amount);
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