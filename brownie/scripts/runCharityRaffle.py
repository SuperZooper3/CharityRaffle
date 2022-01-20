from scripts.helpers import get_account, get_contract, fund_link, LOCAL_BLOCKCHAIN_ENVIRONMENTS
from brownie import network, accounts, config, CharityRaffle
import time

ticketPrice = 0.01*10**18
exp_time = 604800

def deploy_raffle_contract():
    account = get_account(id="test1")
    print("account:", account)
    raffle = CharityRaffle.deploy(
        exp_time,
        get_contract("vrf_coordinator").address,
        get_contract("link_token").address,
        config["networks"][network.show_active()]["fee"],
        config["networks"][network.show_active()]["keyhash"],
        {'from': account},
        publish_source = config["networks"][network.show_active()].get("verify", False)
        )
    print("Charity raffle@", raffle)
    return raffle

def get_raffle():
    try: 
        if CharityRaffle[-1]: return CharityRaffle[-1]
        else: return deploy_raffle_contract()
    except: 
        return deploy_raffle_contract()

def create_raffle(name, ticketPrice, lenght):
    account = get_account(id="test1")
    raffle = get_raffle()
    createTx = raffle.CreateRaffle(name, ticketPrice, lenght, {'from': account})
    createTx.wait(1)
    print("Created raffle")


def get_raffle_info(id):
    raffle = get_raffle()
    name, beneficiary, winner, startTime, endTime = raffle.GetRaffleInfo(id)
    name, startTime, endTime, ticketCount, ticketPrice = raffle.GetRaffleTicketInfo(id)
    print("RaffleId", id, "RaffleName", name, "Beneficiary", beneficiary, "Winner", winner, "StartTime", startTime, "EndTime", endTime, "TicketCount", ticketCount, "TicketPrice", ticketPrice)

def enter_raffle(id, account, ticketCount = 1, price = 0):
    raffle = get_raffle()
    price = ticketPrice * ticketCount if price == 0 else price
    enterTx = raffle.BuyTickets(id, ticketCount, {'from': account, 'value': price})
    enterTx.wait(1)
    print("Entered raffle")

def collect_change():
    raffle = get_raffle()
    account = get_account(id="test1")
    collectTx = raffle.CollectChange({'from': account})
    collectTx.wait(1)
    # print("Collected change", collectTx.return_value)

def get_change():
    raffle = get_raffle()
    print("Change amount", raffle.change())

def claim_raffle(id, account=get_account(id="test1")):
    raffle = get_raffle()
    claimTx = raffle.ClaimRaffle(id, {'from': account})
    claimTx.wait(1)
    # print("Claimed raffle", claimTx.events)
    return claimTx.events["RequestRandomness"]["requestId"]

def fake_VRF_response(requestId, value):
    raffle = get_raffle()
    print("Fake VRF response")
    callTx = get_contract("vrf_coordinator").callBackWithRandomness(requestId, value, raffle.address, {'from': get_account(id="test1")})
    callTx.wait(1)
    print("Fake VRF response done", callTx.events)

def get_balance(id, account):
    return get_raffle().GetRaffleBalance(id, account)

def main():
    raffle_time = 20
    
    get_raffle()
    id = create_raffle("Test Raffle 2", ticketPrice, raffle_time)
    id = 1
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        print("Rinkeby")
        get_raffle_info(id)
        enter_raffle(id, ticketCount=1, account=get_account(id="test1"))
        get_raffle_info(id)
        enter_raffle(id, ticketCount=3, account=get_account(id="test2"))
        get_raffle_info(id)
        enter_raffle(id, ticketCount=7, account=get_account(id="test3"))
    else:
        print("Local")
        get_raffle_info(id)
        enter_raffle(id, ticketCount=1, account=get_account(index=0))
        get_raffle_info(id)
        enter_raffle(id, ticketCount=3, account=get_account(index=1))
        get_raffle_info(id)
        enter_raffle(id, ticketCount=7, account=get_account(index=2))
    get_raffle_info(id)
    print("Test1",get_balance(id, get_account(index=2).address))
    time.sleep(raffle_time) # Wait for the raffle to end
    print("Waited")
    fund_link(get_raffle().address)
    requestId = claim_raffle(id)
    print("Accounts:", [i for i in accounts])
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:  
        print("Fake VRF response")
        fake_VRF_response(requestId, 3)
        time.sleep(1)
    else:
        time.sleep(200)
    print("Waited for VRF")
    get_raffle_info(id)