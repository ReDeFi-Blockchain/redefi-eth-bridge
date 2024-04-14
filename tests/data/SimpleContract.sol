pragma solidity >= 0.8.17;

contract Billboard {
    string public message;

    constructor(string memory _message) {
        message = _message;
    }

    function writeBillboard(string memory _message) public {
        message = _message;
    }
}