// contracts/CharityRafflev0.1.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@chainlink/contracts/src/v0.8/dev/VRFConsumerBase.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract CharityRaffle is Ownable, VRFConsumerBase {
    using Counters for Counters.Counter;

    address public linkTokenAddress;
    uint256 public linkFee;
    bytes32 public VRFKeyHash;
    // A contstructor to deal with randomness
    uint256 public expirationPeriod;
    constructor(uint256 _expirationPeriod, address _vrfCoordinator, address _linkTokenAddress, uint256 _linkFee, bytes32 _VRFKeyHash) VRFConsumerBase(_vrfCoordinator,_linkTokenAddress){
        linkFee = _linkFee;
        VRFKeyHash = _VRFKeyHash;
        linkTokenAddress = _linkTokenAddress;
        expirationPeriod = _expirationPeriod;
    }

    event RequestRandomness(bytes32 requestId);
    event WinnerChosen(uint256 raffleId, address payable winner, uint256 ticketIndex);
    event RaffleCreated(address beneficiary, uint256 raffleId);

    enum RaffleState {
        Open,
        SelectingWinner,
        Finished,
        Expired 
    }
    // Open: The raffle is open for entry
    // SelectingWinner: The raffle is closed and the winner is being selected
    // Finished: The raffle is finished and the winner has been selected, beneficiary has been paid
    // Expired: The raffle has expired since the benificiary has not ended it

    struct Raffle {
        uint256 id; // unique identifier for the raffle
        string name; // name of the raffle
        uint256 ticketCount; // number of tickets bought for this raffle
        uint256 ticketPrice; // in wei
        address payable beneficiary; // address of the beneficiary
        address payable winner; // address of the winner of the raffle, by default it's 0x0
        uint256 startTime; // unix timestamp of the start of the raffle
        uint256 endTime; // unix timestamp of the end of the raffle
        RaffleState state; // state of the raffle
        mapping(address => uint256) ticketBalances; // mapping of address to ticket count
        address[] ticketOwners; // array of addresses of the ticket owners (used for iteration through the ticket balances)
        bool paidOut; // whether the raffle has been payed out
    }

    // Some rules of how raffles work
    // 1. Anyone can make a new raffle
    // 2. Anyone can buy tickets for any open raffle, and this can be for multiple raffles
    // 3. Tickets are only refundable if the raffle expires, this means that the beneficiary has not claimed the raffle a week after it's end
    // 4. The beneficiary can only end the raffle after the end time

    Counters.Counter public RaffleCount;
    mapping(uint256 => Raffle) public Raffles; // mapping of raffle id to raffle data
    mapping(bytes32 => uint256) public VRFRequestIdTORaffleId; // mapping of VRF request id to raffle id

    // A value that keeps track of all the change givent to the contract
    uint256 public change = 0;

    function CreateRaffle(string memory _raffleName, uint256 _ticketPrice, uint256 _raffleLength) public returns(uint256 raffleId){
        RaffleCount.increment();
        uint256 _id = RaffleCount.current();
        Raffle storage raffle = Raffles[_id]; 
        raffle.id = _id;
        raffle.name = _raffleName;
        raffle.ticketCount = 0;
        raffle.ticketPrice = _ticketPrice;
        raffle.beneficiary = payable(msg.sender);
        raffle.startTime = block.timestamp;
        raffle.endTime = block.timestamp + _raffleLength;
        raffle.state = RaffleState.Open;
        raffle.winner = payable(0x0);
        emit RaffleCreated(raffle.beneficiary, _id);
    }

    // Some reader functions for getting info about raffles
    function GetRaffleInfo(uint256 _id) public view returns (string memory name, address payable beneficiary, address payable winner, uint256 startTime, uint256 endTime) {
        return (Raffles[_id].name, Raffles[_id].beneficiary, Raffles[_id].winner, Raffles[_id].startTime, Raffles[_id].endTime);
    }

    function GetRaffleTicketInfo(uint256 _id) public view returns (string memory name, uint256 startTime, uint256 endTime, uint256 ticketCount, uint256 ticketPrice) {
        return (Raffles[_id].name, Raffles[_id].startTime, Raffles[_id].endTime, Raffles[_id].ticketCount, Raffles[_id].ticketPrice);
    }

    function GetRaffleBalance(uint256 _id, address owner) public view returns (uint256 balance) {
        return Raffles[_id].ticketBalances[owner];
    }

    function GetRaffleCount() public view returns (uint256) {
        return RaffleCount.current();
    }

    function ClaimRaffle(uint256 _id) public{
        require(msg.sender == Raffles[_id].beneficiary, "Only the beneficiary can claim the raffle");
        require(block.timestamp >= Raffles[_id].endTime, "The raffle has not closed yet");
        require(Raffles[_id].endTime + expirationPeriod > block.timestamp, "The raffle has expired and cannot be claimed");
        require(Raffles[_id].state == RaffleState.Open, "The raffle is not avaible for claiming");
        require(IERC20(linkTokenAddress).balanceOf(address(this)) >=  linkFee, "The contract needs to be paid link token to claim the raffle");
        Raffles[_id].state = RaffleState.SelectingWinner;
        // Fire off the VRF to select the winner
        bytes32 requestId = requestRandomness(VRFKeyHash, linkFee); // Return a bytes 32 which is the request ID
        VRFRequestIdTORaffleId[requestId] = _id; // Map the request ID to the raffle ID
        emit RequestRandomness(requestId);
    }

    // This is run by the VRF coordinator to finalize the winner
    function fulfillRandomness(bytes32 _requestId, uint256 _randomness) internal override {
        uint256 raffleId = VRFRequestIdTORaffleId[_requestId];
        require(Raffles[raffleId].state == RaffleState.SelectingWinner, "The raffle is not in the SelectingWinner state");
        require(_randomness >= 0, "No randomness found");
        Raffles[raffleId].state = RaffleState.Finished;
        uint256 winningTicketIndex = _randomness % Raffles[raffleId].ticketCount;
        // Todo: Convert the winning ticket index to an address
        uint256 ticketCounter = 0;
        uint256 l = Raffles[raffleId].ticketOwners.length;
        for (uint256 i = 0; i < l; i++) {
            uint256 balance = Raffles[raffleId].ticketBalances[Raffles[raffleId].ticketOwners[i]];
            if (ticketCounter <= winningTicketIndex && winningTicketIndex < ticketCounter + balance) { // We have found the winning ticket
                Raffles[raffleId].winner = payable(Raffles[raffleId].ticketOwners[i]);
                break;
            }
            ticketCounter += balance;
        }
        // Send the raffle money to the beneficiary
        (Raffles[raffleId].paidOut, ) = payable(Raffles[raffleId].beneficiary).call{value: Raffles[raffleId].ticketPrice * Raffles[raffleId].ticketCount}("");
        emit WinnerChosen(raffleId, Raffles[raffleId].winner, winningTicketIndex);
    }

    // A function to buy tickets for a raffle
    function BuyTickets(uint256 raffleId, uint256 _ticketCount) public payable {
        require(Raffles[raffleId].state == RaffleState.Open, "Raffle not open");
        require(block.timestamp < Raffles[raffleId].endTime, "Raffle is closed");
        require(_ticketCount > 0, "Ticket count must be greater than 0");
        require(msg.value >= Raffles[raffleId].ticketPrice * _ticketCount, "Ticket price is greater than the amount sent");
        Raffles[raffleId].ticketCount += _ticketCount;
        if (Raffles[raffleId].ticketBalances[msg.sender] == 0) { // This will be a list of all of the unique ticket owners (in the order they buy them but that dosent matter dose it)
            Raffles[raffleId].ticketOwners.push(msg.sender);
        }
        Raffles[raffleId].ticketBalances[msg.sender] += _ticketCount;
        // If the buyer is not in the ticket owners array, add him
        change += msg.value - Raffles[raffleId].ticketPrice * _ticketCount;
    }

    // A function for the owner of the contract to collect all the change in the contract
    function CollectChange() public onlyOwner returns (uint256){
        require(change > 0, "There is no change to collect!");
        payable(msg.sender).call{value: change}("");
        uint256 _change = change;
        change = 0;
        return _change;
    }

    // A function for ticket buys to be refunded all the tickets they own
    function TicketRefund(uint256 raffleId) public{
        require(block.timestamp >= Raffles[raffleId].endTime + expirationPeriod, "The refund period has not ended yet");
        require(Raffles[raffleId].state != RaffleState.Finished, "The raffle is finished");
        require(Raffles[raffleId].state != RaffleState.SelectingWinner, "The raffle is selecting a winner.");
        // Update the expiration of the raffle
        Raffles[raffleId].state = RaffleState.Expired;
        // Send the money back to the buyer
        (bool transfered, ) = payable(msg.sender).call{value: Raffles[raffleId].ticketPrice * Raffles[raffleId].ticketBalances[msg.sender]}("");
        if (transfered) {
            Raffles[raffleId].ticketBalances[msg.sender] = 0;
        }
    }
}