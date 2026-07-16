// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract AgentEscrow {
    struct Escrow {
        address payer;
        address payee;
        address arbiter; // Our AI ASP Backend
        uint256 amount;
        string taskDescription;
        bool isFunded;
        bool isResolved;
    }

    mapping(uint256 => Escrow) public escrows;
    uint256 public nextEscrowId;

    event EscrowCreated(uint256 indexed escrowId, address payer, address payee, address arbiter, uint256 amount, string taskDescription);
    event EscrowResolved(uint256 indexed escrowId, bool success);

    // Agent A creates an escrow and locks native tokens (e.g. OKB on X Layer)
    function createEscrow(address _payee, address _arbiter, string memory _taskDescription) external payable returns (uint256) {
        require(msg.value > 0, "Must fund escrow");
        
        uint256 escrowId = nextEscrowId++;
        escrows[escrowId] = Escrow({
            payer: msg.sender,
            payee: _payee,
            arbiter: _arbiter,
            amount: msg.value,
            taskDescription: _taskDescription,
            isFunded: true,
            isResolved: false
        });

        emit EscrowCreated(escrowId, msg.sender, _payee, _arbiter, msg.value, _taskDescription);
        return escrowId;
    }

    // The arbiter (Our AI ASP) decides the outcome after evaluating the work.
    // success = true -> pay Agent B (payee). success = false -> refund Agent A (payer).
    function resolveEscrow(uint256 _escrowId, bool _success) external {
        Escrow storage e = escrows[_escrowId];
        require(e.isFunded && !e.isResolved, "Escrow not active");
        require(msg.sender == e.arbiter, "Only arbiter can resolve");

        e.isResolved = true;
        e.isFunded = false;

        if (_success) {
            payable(e.payee).transfer(e.amount);
        } else {
            payable(e.payer).transfer(e.amount);
        }

        emit EscrowResolved(_escrowId, _success);
    }
}
