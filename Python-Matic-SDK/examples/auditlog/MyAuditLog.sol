pragma solidity ^0.5.17;
pragma experimental ABIEncoderV2;

contract myAuditLog {
    event AuditLogAdded(address changedBy, uint256 timestamp);
    
    struct AuditLog {
        string note;
        uint256 incrementedValue;
        uint256 timestamp;
    }
    mapping(address => AuditLog[]) public storedAuditLogs;

    constructor() public {
    }

    function addAuditLog(string memory _newNote, address _changedBy, uint256 _incrementValue, uint256 _timestamp)
    public
   
    {
        AuditLog memory _a = AuditLog(_newNote, _incrementValue, _timestamp);
        storedAuditLogs[_changedBy].push(_a);
        emit AuditLogAdded(_changedBy, block.timestamp);
    }

    function getLogsBySender(address _sender)
    public view
    returns (AuditLog[] memory auditLogs)
    {
        AuditLog[] memory audit_logs = new AuditLog[](storedAuditLogs[_sender].length);
        for (uint i = 0; i<storedAuditLogs[_sender].length; i++) {
            audit_logs[i] = storedAuditLogs[_sender][i];
        }
        return audit_logs;
    }
}
