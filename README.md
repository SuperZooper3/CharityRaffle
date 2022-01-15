# CharityRaffle
 An Ethereum Smart Contract CharityRaffle.
 **Currently only on RINKEBY**

## Description
This smart contract is used to create a raffle for a charity.

## Raffle Details
A raffle is composed of:
- An identifier (id- sequential number, 1 indexed)
- A name (name- string)
- A beneficiary, the one to which the procedes of the raffle will be paid (beneficiary- address)
- An start date (startTime- uint256 unix timestamp)
- An end date (endTime- uint256 unix timestamp)
- A ticket price (ticketPrice- uint256 in wei)
- A ticket count, the number of purchased tickets (ticketCount- uint256)
- The ticket balance of all the ticket owners (ticketBalances- address => uint256)
- A list of ticket owners, used for itteration (ticketOwners- address[])
- A state of the raffle (state- uint8)
  - Open: 0
  - SelectingWinner: 1
  - Finished: 2
  - Expired: 3
- A bool to track if the winnings have been paid out (paidOut- bool)

## Raffle Rules
1. Anyone can make a new raffle
2. Anyone can buy tickets for any open raffle, and this can be for multiple raffles
3. Tickets are only refundable if the raffle expires, this means that the beneficiary has not claimed the raffle a week after it's end
4. The beneficiary can only end the raffle after the end time

## Functions
### CreateRaffle
`CreateRaffle(string memory _raffleName, uint256 _ticketPrice, uint256 _raffleLength) public returns(uint256 raffleId)`
This function takes in the name of the raffle (a string), the ticket price (in WEI), and the length of the raffle (in seconds).
Warning: The raffle start and end times are based on when the transaction is mined.

### BuyTickets
`BuyTickets(uint256 raffleId, uint256 _ticketCount) public payable`
The function used to buy tickets for a raffle.
The functions takes in the raffleId and the number of tickets to purchase.
The raffle must be open to purchase tickets (the state must be open and the time must be within the raffle time).
You must buy at least 1 ticket and the value transfered must be at least the ticket price.

### TicketRefund
`TicketRefund(uint256 raffleId) public`
This function is used to refund the tickets you have purchased if the raffle expires.
The function takes in the raffleId and will transfer the ticket owner the value of all the tickets they bought.

### ClaimRaffle
`ClaimRaffle(uint256 raffleId) public`
This is the function called by the beneficiary to claim the raffle.
The function takes the id of the raffle being claimed. 
Contract **must** have enough LINK token to pay out the raffle since it will be using the Chainlink VRF system to pick the winner.
The function dose not instantly transfer the funds or set the winner as the VRF needs to respond.
The VRF will call `fulfillRandomness` which will transfer the funds and set the winner.

### CollectChange
`CollectChange() public onlyOwner returns (uint256)`
This is a function that can be run by the contract owner to collect the change that is left over from ticket purchases that overpay.

### GetRaffleInfo, GetRaffleTicketInfo
`GetRaffleInfo(uint256 _id) public view returns (string memory name, address payable beneficiary, address payable winner, uint256 startTime, uint256 endTime)`
and
`GetRaffleTicketInfo(uint256 _id) public view returns (string memory name, uint256 startTime, uint256 endTime, uint256 ticketCount, uint256 ticketPrice)`
These functions are used to get the raffle information for a given raffleId. These two functions are split up since a single function wasnt able to return all the information.

### GetRaffleBalance
`GetRaffleBalance(uint256 _id, address owner) public view returns (uint256 balance)`
This function is used to get the balance of a raffle for a given owner.

## Other Global Variables
### RaffleCount
The number of raffles, uses the openzeppelin counter.

### expirationPeriod
The number of seconds before a raffle expires (by design should be a week).

### linkTokenAddress, linkFee, VRFKeyHash
These are the addresses of the LINK token on the given network, the LINK fee needed to call the VRF, and the VRF key hash.
Read more at https://docs.chain.link/docs/chainlink-vrf/.

## Contract Dependencies
- [Chainlink VRF](https://docs.chain.link/docs/chainlink-vrf/) to generate randomness for the winner.
- [OpenZepplin Counters](https://docs.openzeppelin.com/contracts/4.x/api/utils#Counters) to get raffle Ids.
- [OpenZepplin Access Control](https://docs.openzeppelin.com/contracts/4.x/access-control) to track the owner for change collection.

## Brownie Setup
- Install all the dependencies in requirements.txt using `pip install -r requirements.txt` (preferably using a virtual environment)
- Add a .env file to /brownie with in it:
  - An infura key for easy network access in `WEB3_INFURA_PROJECT_ID` 
  - An etherscan API tokoen for contract verification in `ETHERSCAN_TOKEN`
- `cd brownie` && `brownie compile` to compile the smart contract
- Use `brownie test` to test the smart contract.
- Use `brownie run scripts\deploy.py` to deploy the smart contract to a local network. (Add the --network NETWORKNAME flag to deploy it to a real network).

## Interacton with the frontend
If you want to use this smart contract with a frontend, I have made one at https://github.com/SuperZooper3/charity-raffle-front-end. There is a running version at https://eth-charity-raffle.herokuapp.com/.

If you want to test the frontend locally with this smart contract, make sure to put the two repositories in the same directory. Ex:
...\Blockchain:
  -> charity-raffle-front-end
  -> CharityRaffle

## Futre Improvements
- Add an automatic NFT given out to the winner as some kind of a prize.
- Let raffles be created for beneciaries other than the raffle creator.
- Let raffle creators add other NFT or ERC20 tokens as raffle prizes.
- Accept ERC20 tokens for raffles.

## Warnings
This contract has not been audited and it is my first real smart contract so I do not expect it to be perfect. It has been tested extensively and is working as intended on a local machine and on the Rinkeby Testnet but might not work on other networks.
It comes as is with no warranty and is not intended for use in production.
