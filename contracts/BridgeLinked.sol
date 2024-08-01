// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

interface IERC20 {
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
	/// @notice Emitted when a deposit is made to the bridge
	/// @param token The address of the token being deposited
	/// @param receiver The address of the receiver on the target chain
	/// @param amount The amount of tokens being deposited
	/// @param targetChainId The ID of the target chain
	event Deposit(address indexed token, address indexed receiver, uint amount, uint targetChainId);

	/// @notice Emitted when a transfer is executed from the bridge
	/// @param txHash The transaction hash
	/// @param amount The amount of tokens being transferred
	event Transfer(bytes32 indexed txHash, uint amount);

	/// @notice Emitted when a transaction is listed on the bridge
	/// @param txHash The transaction hash
	/// @param sourceChainId The ID of the source chain
	event Listed(bytes32 indexed txHash, uint sourceChainId);

	/// @notice Emitted when a transaction is confirmed by a validator
	/// @param txHash The transaction hash
	/// @param validatorId The ID of the validator
	event Confirmed(bytes32 indexed txHash, uint16 validatorId);

	/// @notice Emitted when funds are added or withdrawn from the bridge
	/// @param funder The address of the funder
	/// @param token The address of the token
	/// @param amount The amount of tokens
	/// @param isWithdraw Indicates if the funds were withdrawn
	event Funded(address indexed funder, address indexed token, uint256 amount, bool isWithdraw);

	/// @notice Emitted when a new admin is set
	/// @param admin The address of the new admin
	event NewAdmin(address indexed admin);

	/// @notice Emitted when a new signer is set
	/// @param signer The address of the new signer
	event NewSigner(address indexed signer);

	/// @notice Emitted when a new validator is added
	/// @param validator The address of the new validator
	event NewValidator(address indexed validator);

	/// @notice Emitted when a validator is removed
	/// @param validator The address of the removed validator
	event RemovedValidator(address indexed validator);

	/// @notice Emitted when the maintenance state is changed
	/// @param state The new maintenance state
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

	mapping(address => TokenData) public registeredTokens;
	address[] public tokens;

	/// @notice Initializes the contract with the admin address
	/// @param _admin The address of the admin
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

	/// @notice Sets a new admin
	/// @param _admin The address of the new admin
	function setAdmin(address _admin) external onlyOwner {
		admin = _admin;
		emit NewAdmin(_admin);
	}

	/// @notice Switches the maintenance state of the bridge
	/// @param _state The new maintenance state
	function switchMaintenance(bool _state) external onlyAdmin {
		isMaintenanceEnabled = _state;
		emit MaintenanceState(_state);
	}

	/// @notice Sets a new signer
	/// @param _signer The address of the new signer
	function setSigner(address _signer) external onlyAdmin {
		signer = _signer;
		emit NewSigner(_signer);
	}

	/// @notice Sets the required number of confirmations for a transaction to be executed by validators.
	/// @dev The number of confirmations represents the minimum number of validators that must confirm a transaction before it can be executed. Validators play a crucial role in ensuring the legitimacy and security of cross-chain transactions.
	/// @param _confirmations The number of required confirmations.
	function setRequiredConfirmations(uint16 _confirmations) external onlyAdmin {
		requiredConfirmations = _confirmations;
	}

	/// @notice Checks if an address is a validator
	/// @param _validator The address to check
	/// @return True if the address is a validator, false otherwise
	function isValidator(address _validator) public view returns (bool) {
		return validatorIds[_validator] > 0 && !isValidatorDeleted[_validator];
	}

	/// @notice Adds new validators
	/// @param _validators The addresses of the new validators
	function addValidators(address[] memory _validators) external onlyAdmin {
		for(uint i = 0; i < _validators.length; i++) {
			require(validators.length <= type(uint16).max, "bridge: validators count exceeds uint16 range");
			require(validatorIds[_validators[i]] < 1, "bridge: validator already exists");
			validators.push(_validators[i]);
			validatorIds[_validators[i]] = uint16(validators.length);
			emit NewValidator(_validators[i]);
		}
	}

	/// @notice Adds a new link to the bridge on the specified chain.
	/// @param _chainId The ID of the target chain to link.
	/// @param _contractAddress The address of the bridge contract on the target chain.
	function addLink(uint _chainId, address _contractAddress) external onlyAdmin {
		require(links[_chainId] == address(0), "bridge: link for this contract already set");
		links[_chainId] = _contractAddress;
	}

	/// @notice Adds a new token pair for cross-chain transactions.
	/// @dev Creates a mapping between a source token address and a destination chain with its corresponding token address. This enables tokens to be transferred between the current chain and the target chain.
	/// @param _sourceAddress The address of the source token on the current chain.
	/// @param _destinationChainId The ID of the destination chain where the token will be sent.
	/// @param _destinationAddress The address of the token on the destination chain.
	function addPair(address _sourceAddress, uint _destinationChainId, address _destinationAddress) external onlyAdmin {
		require(!hasPair(_sourceAddress, _destinationChainId), "bridge: pair already exists");
		pairs.push(PairData(_sourceAddress, _destinationChainId, _destinationAddress));
	}

	/// @notice Removes a token pair
	/// @param _sourceAddress The source token address
	/// @param _destinationChainId The destination chain ID
	function removePair(address _sourceAddress, uint _destinationChainId) external onlyAdmin {
		require(hasPair(_sourceAddress, _destinationChainId), "bridge: invalid pair");
		for(uint i = 0; i < pairs.length; i++) {
			if(pairs[i].sourceAddress == _sourceAddress && pairs[i].destinationChainId == _destinationChainId && !isPairDeleted[uint16(i)]) {
				isPairDeleted[uint16(i)] = true;
			}
		}
	}

	/// @notice Checks if a token pair exists
	/// @param _sourceAddress The source token address
	/// @param _destinationChainId The destination chain ID
	/// @return True if the pair exists, false otherwise
	function hasPair(address _sourceAddress, uint _destinationChainId) public view returns (bool) {
		for(uint i = 0; i < pairs.length; i++) {
			if(pairs[i].sourceAddress == _sourceAddress && pairs[i].destinationChainId == _destinationChainId && !isPairDeleted[uint16(i)]) return true;
		}
		return false;
	}

	/// @notice Gets the destination address for a token pair
	/// @param _sourceAddress The source token address
	/// @param _destinationChainId The destination chain ID
	/// @return The destination token address
	function getDestinationAddress(address _sourceAddress, uint _destinationChainId) public view returns (address) {
		for(uint i = 0; i < pairs.length; i++) {
			if(pairs[i].sourceAddress == _sourceAddress && pairs[i].destinationChainId == _destinationChainId && !isPairDeleted[uint16(i)]) return pairs[i].destinationAddress;
		}
		return address(0);
	}

	/// @notice Changes the state of a validator (active or deleted).
	/// @dev Sets the deletion status of a validator, which affects their ability to confirm transactions.
	/// @param _validator The address of the validator.
	/// @param _isDeleted The deletion status (true if the validator is to be marked as deleted, false otherwise).
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

	/// @notice Checks if a transaction hash is confirmed by a specific validator.
	/// @param _txHash The transaction hash.
	/// @param _validator The address of the validator.
	/// @return True if the transaction hash is confirmed by the validator, false otherwise.
	function isConfirmedBy(bytes32 _txHash, address _validator) public view returns (bool) {
		uint16 _validatorId = validatorIds[_validator];
		for(uint i = 0; i < confirmations[_txHash].confirmedBy.length; i++) {
			if(confirmations[_txHash].confirmedBy[i] == _validatorId) return true;
		}
		return false;
	}

	/// @notice Gets the list of validator IDs that confirmed a specific transaction hash.
	/// @param _txHash The transaction hash.
	/// @return An array of validator IDs that confirmed the transaction hash.
	function confirmedBy(bytes32 _txHash) public view returns (uint16[] memory) {
		return confirmations[_txHash].confirmedBy;
	}

	/// @notice Confirms one or more transaction hashes.
	/// @dev Validators use this function to confirm transactions, which is required for the transaction to be executed.
	/// @param _txHashes An array of transaction hashes to be confirmed.
	function confirm(bytes32[] memory _txHashes) external onlyValidator {
		for(uint i = 0; i < _txHashes.length; i++) {
			require(confirmations[_txHashes[i]].amount > 0, "bridge: unknown txHash");
			require(!confirmations[_txHashes[i]].isSent, "bridge: txHash already sent");
		}

		for(uint i = 0; i < _txHashes.length; i++) {
			require(!isConfirmedBy(_txHashes[i], msg.sender), "bridge: txHash already confirmed");
			confirmations[_txHashes[i]].confirmedBy.push(validatorIds[msg.sender]);
			emit Confirmed(_txHashes[i], validatorIds[msg.sender]);
		}
	}

	/// @notice Changes the ownership status of a registered token.
	/// @dev Sets whether a token is owned by the bridge, affecting how the token is handled during transactions.
	/// @param _token The address of the token.
	/// @param _status The new ownership status (true if the token is owned by the bridge, false otherwise).
	function changeTokenOwnership(address _token, bool _status) external onlyAdmin {
		require(registeredTokens[_token].tokenId > 0, "bridge: token must by registered first");
		registeredTokens[_token].isOwn = _status;
	}

	/// @notice Registers a list of new tokens for the bridge.
	/// @dev Adds new tokens to the bridge, allowing them to be used in cross-chain transactions.
	/// @param _tokens An array of token addresses to be registered.
	function registerTokens(address[] memory _tokens) external onlyAdmin {
		for (uint i = 0; i < _tokens.length; i++) {
			require(tokens.length <= type(uint16).max, "bridge: tokens count exceeds uint16 range");
			require(registeredTokens[_tokens[i]].tokenId < 1, "bridge: token already exists");

			tokens.push(_tokens[i]);
			registeredTokens[_tokens[i]].tokenId = uint16(tokens.length);
		}
	}

	/// @notice Adds funds to the bridge for a specific token.
	/// @dev Allows users to add funds to the bridge for cross-chain transactions. Only active when the bridge is not in maintenance mode.
	/// @param _token The address of the token.
	/// @param _amount The amount of tokens to add.
	function addFunds(address _token, uint256 _amount) external payable onlyWithActiveBridge {
		require(_amount > 0, "bridge: amount must be greater than zero");
		require(registeredTokens[_token].tokenId > 0, "bridge: token should be registered first");
		require(!registeredTokens[_token].isOwn, "bridge: no need any funds for owned tokens");
		if(_token == address(0)) {
			require(msg.value == _amount, "bridge: invalid amount");
		}
		else {
			TransferHelper.safeTransferFrom(_token, msg.sender, address(this), _amount);
		}
		registeredTokens[_token].funds[msg.sender] += _amount;
		emit Funded(msg.sender, _token, _amount, false);
	}

	/// @notice Withdraws funds from the bridge for a specific token.
	/// @dev Allows users to withdraw their funds from the bridge.
	/// @param _token The address of the token.
	/// @param _amount The amount of tokens to withdraw.
	function withdrawFunds(address _token, uint256 _amount) external {
		require(_amount > 0, "bridge: amount must be greater than zero");
		require(registeredTokens[_token].tokenId > 0, "bridge: token should be registered first");
		require(!registeredTokens[_token].isOwn, "bridge: no need any funds for owned tokens");
		require(registeredTokens[_token].funds[msg.sender] >= _amount, "bridge: invalid amount");

		registeredTokens[_token].funds[msg.sender] -= _amount;

		if(_token == address(0)) {
			TransferHelper.safeTransferETH(msg.sender, _amount);
		}
		else {
			TransferHelper.safeTransfer(_token, msg.sender, _amount);
		}
		emit Funded(msg.sender, _token, _amount, true);
	}

	/// @notice Deposits tokens to the bridge for cross-chain transfer.
	/// @dev Allows users to deposit tokens to the bridge, which will be transferred to the specified address on the target chain.
	/// @param _receiver The address of the receiver on the target chain.
	/// @param _token The address of the token being deposited.
	/// @param _amount The amount of tokens being deposited.
	/// @param _targetChainId The ID of the target chain.
	function deposit(address _receiver, address _token, uint _amount, uint _targetChainId) external payable onlyWithActiveBridge {
		require(_amount > 0, "bridge: amount must be greater than zero");
		require(msg.sender != address(0) && _receiver != address(0), "bridge: zero receiver");
		require(registeredTokens[_token].tokenId > 0, "bridge: unable to deposit unregistered token");
		require(links[_targetChainId] != address(0), "bridge: no link to target chainId");
		if (_token == address(0)) {
			require(msg.value == _amount, "bridge: invalid amount");
		} else {
			if (registeredTokens[_token].isOwn) {
				IERC20(_token).burnFrom(msg.sender, _amount);
			} else {
				TransferHelper.safeTransferFrom(_token, msg.sender, address(this), _amount);
			}
		}
		emit Deposit(_token, _receiver, _amount, _targetChainId);
	}

	/// @notice Lists transactions for cross-chain transfer.
	/// @dev This function is used by the signer to list transactions, preparing them for confirmation by validators.
	/// @param _args A 2D array containing transaction details. Each inner array should contain the source token address, destination address, amount, source chain ID, and transaction hash.
	function list(uint[][] memory _args) external onlySigner {
		for(uint i = 0; i < _args.length; i++) {
			uint _sourceChainId = _args[i][3];
			require(links[_sourceChainId] != address(0), "bridge: no link to source chainId");
			address _token = address(uint160(_args[i][0]));
			uint16 _tokenId = registeredTokens[_token].tokenId;
			require(_tokenId > 0, "bridge: trying to list unregistered token");
			address _to = address(uint160(_args[i][1]));
			uint _amount = _args[i][2];
			bytes32 _txHash = bytes32(_args[i][4]);
			require(_amount > 0, "bridge: amount must be more than zero");
			require(confirmations[_txHash].amount == 0, "bridge: txHash already listed");
			confirmations[_txHash].tokenId = _tokenId;
			confirmations[_txHash].receiver = _to;
			confirmations[_txHash].amount = _amount;
			emit Listed(_txHash, _sourceChainId);
		}
	}

	/// @notice Transfers tokens based on confirmed transaction hashes.
	/// @dev This function is used by the signer to transfer tokens to the destination addresses after sufficient confirmations have been received. It ensures that only transactions that have received the required number of validator confirmations are executed.
	/// @param _txHashes An array of transaction hashes to be processed for transfer.
	function transfer(bytes32[] memory _txHashes) external onlySigner {
		for(uint i = 0; i < _txHashes.length; i++) {
			bytes32 _txHash = _txHashes[i];
			if (!confirmations[_txHash].isSent && confirmations[_txHash].confirmedBy.length >= requiredConfirmations) {
				uint16 _tokenId = confirmations[_txHash].tokenId;
				address _token = tokens[_tokenId - 1];
				address _to = confirmations[_txHash].receiver;
				uint256 _amount = confirmations[_txHash].amount;
				confirmations[_txHash].isSent = true;
				if (_token==address(0)) {
					TransferHelper.safeTransferETH(_to, _amount);
				} else {
					if (registeredTokens[_token].isOwn) {
						IERC20(_token).mint(_to, _amount);
					} else {
						TransferHelper.safeTransfer(_token, _to, _amount);
					}
				}
				emit Transfer(_txHash, _amount);
			}
		}
	}
}