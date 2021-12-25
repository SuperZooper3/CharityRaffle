from scripts.helpers import get_account, smart_get_account, get_contract, fund_link, LOCAL_BLOCKCHAIN_ENVIRONMENTS
from brownie import network, accounts, config, CharityRaffle
import time
import pytest
from random import randint

ticketPrice = 0.001*10**18

exp_time, length = 0, 0

def init_values():
    global exp_time, length
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        length = 10
        exp_time = 5 
    else:
        length = 240
        exp_time = 120 

def deploy_raffle_contract():
    account = smart_get_account(0)
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

def fake_VRF_response(raffle, requestId, value):
    print("Fake VRF response")
    callTx = get_contract("vrf_coordinator").callBackWithRandomness(requestId, value, raffle.address, {'from': smart_get_account(0)})
    callTx.wait(1)
    print("Fake VRF response done", callTx.events)
    time.sleep(1)

# All of the tests here:
# - Deploy a raffle contract
# - Create a raffle
# - Buy tickets
# - Buy a ticket without paying enough
# - Keep track of the change correclty
# - Collect the change
# - Check that only the owner can collect the change
# - Test getting a refund
# - Test getting a refund when the raffle is not over
# - Test that a refund can't be gotten while the raffle is getting finished
# - Test that only the beneificary can claim the raffle
# - Test that the raffle can't be claimed before the end time
# - Test that the raffle can't be claimed after the expirey time
# - Test picking different winners
# - Test storing the ticket buyers

def test_deploy_raffle_contract():
    init_values()
    raffle = deploy_raffle_contract()

def test_create_raffle():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    # Act
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Assert
    Dname, Dbeneficiary, Dwinner, DstartTime, DendTime = raffle.GetRaffleInfo(1)
    assert raffle.RaffleCount() == 1
    assert Dname == name
    assert Dbeneficiary == smart_get_account(0)
    assert Dwinner == "0x0000000000000000000000000000000000000000"
    assert DstartTime < DendTime
    assert DstartTime + length == DendTime
    assert DstartTime <= int(time.time()) # It dosent start in the future

def test_ticket_buying():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    print(createTx.return_value)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 2, {'from': smart_get_account(2), 'value': ticketPrice*2})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 5, {'from': smart_get_account(3), 'value': ticketPrice*5})
    enterTx.wait(1)
    # Assert
    assert raffle.GetRaffleBalance(1, smart_get_account(1)) == 1
    assert raffle.GetRaffleBalance(1, smart_get_account(2)) == 2
    assert raffle.GetRaffleBalance(1, smart_get_account(3)) == 5

def test_buy_ticket_without_paying_enough():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    with pytest.raises(Exception):
        enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice-100})
        enterTx.wait(1)

def test_ticket_change_tracked():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice+100})
    enterTx.wait(1)
    # Assert
    assert raffle.change() == 100

def test_collect_change():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice+100})
    enterTx.wait(1)
    # Assert
    assert raffle.change() == 100
    collectTx = raffle.CollectChange({'from': smart_get_account(0)})
    collectTx.wait(1)
    assert raffle.change() == 0

def test_only_owner_can_collect_change():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice+100})
    enterTx.wait(1)
    # Assert
    with pytest.raises(Exception):
        refundTx = raffle.CollectChange({'from': smart_get_account(1)})
        refundTx.wait(1)

def test_ticket_refund():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice+100})
    enterTx.wait(1)
    # Assert
    print(length+exp_time)
    time.sleep(length+exp_time)
    beforeRefundEthBalance = smart_get_account(1).balance()
    refundTx = raffle.TicketRefund(1, {'from': smart_get_account(1)})
    refundTx.wait(1)
    assert raffle.GetRaffleBalance(1, smart_get_account(1)) == 0
    assert smart_get_account(1).balance() > beforeRefundEthBalance # We get some ETH back (dosent deal with gas prices)

def test_cannot_refund_before_end():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice+100})
    enterTx.wait(1)
    # Assert
    with pytest.raises(Exception):
        refundTx = raffle.TicketRefund(1, {'from': smart_get_account(1)})
        refundTx.wait(1)

def test_cannot_refund_while_selecting_winner():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice+100})
    enterTx.wait(1)
    # Now we trigger the end of the raffle
    print(length, network.show_active())
    time.sleep(length)
    fund_link(raffle.address, account=smart_get_account(0))
    claimTx = raffle.ClaimRaffle(1, {'from': smart_get_account(0)})
    claimTx.wait(1)
    time.sleep(exp_time)
    # Assert
    with pytest.raises(Exception):
        refundTx = raffle.TicketRefund(1, {'from': smart_get_account(1)})
        refundTx.wait(1)

def test_only_ben_can_claim():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice})
    enterTx.wait(1)
    # Now we trigger the end of the raffle
    time.sleep(length)
    # Assert
    with pytest.raises(Exception):
        claimTx = raffle.ClaimRaffle(1, {'from': smart_get_account(1)})
        claimTx.wait(1)

def test_cannot_claim_before_end():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice})
    enterTx.wait(1)
    # Assert
    with pytest.raises(Exception):
        claimTx = raffle.ClaimRaffle(1, {'from': smart_get_account(0)})
        claimTx.wait(1)

def test_cannot_claim_after_expired():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice})
    enterTx.wait(1)
    # Now we trigger the end of the raffle and miss the expiry time
    time.sleep(length+exp_time+1)
    # Assert
    with pytest.raises(Exception):
        claimTx = raffle.ClaimRaffle(1, {'from': smart_get_account(0)})
        claimTx.wait(1)

def test_correctly_pick_winner_zero():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    # Act
    createTx.wait(1)
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 2, {'from': smart_get_account(2), 'value': ticketPrice*2})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 5, {'from': smart_get_account(3), 'value': ticketPrice*5})
    enterTx.wait(1)
    # Now we trigger the end of the raffle
    print(length)
    time.sleep(length)
    fund_link(raffle.address, account=smart_get_account(0))
    claimTx = raffle.ClaimRaffle(1, {'from': smart_get_account(0)})
    claimTx.wait(1)
    requestId = claimTx.events['RequestRandomness']['requestId'] 
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        fake_VRF_response(raffle,requestId, 0)
    # Assert
    Dname, Dbeneficiary, Dwinner, DstartTime, DendTime = raffle.GetRaffleInfo(1)
    print(raffle.GetRaffleInfo(1))
    assert Dwinner == smart_get_account(1).address

def test_correctly_pick_winner_last():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    # Act
    createTx.wait(1)
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 2, {'from': smart_get_account(2), 'value': ticketPrice*2})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 5, {'from': smart_get_account(3), 'value': ticketPrice*5})
    enterTx.wait(1)
    # Now we trigger the end of the raffle
    time.sleep(length)
    fund_link(raffle.address, account=smart_get_account(0))
    claimTx = raffle.ClaimRaffle(1, {'from': smart_get_account(0)})
    claimTx.wait(1)
    requestId = claimTx.events['RequestRandomness']['requestId']
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        fake_VRF_response(raffle,requestId, 7)
    # Assert
    Dname, Dbeneficiary, Dwinner, DstartTime, DendTime = raffle.GetRaffleInfo(1)
    print(raffle.GetRaffleInfo(1))
    assert Dwinner == smart_get_account(3).address

def test_correctly_pick_winner_big():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    # Act
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 2, {'from': smart_get_account(2), 'value': ticketPrice*2})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 5, {'from': smart_get_account(3), 'value': ticketPrice*5})
    enterTx.wait(1)
    # Now we trigger the end of the raffle
    time.sleep(length)
    fund_link(raffle.address, account=smart_get_account(0))
    claimTx = raffle.ClaimRaffle(1, {'from': smart_get_account(0)})
    claimTx.wait(1)
    requestId = claimTx.events['RequestRandomness']['requestId']
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        fake_VRF_response(raffle,requestId, 800)
    # Assert
    Dname, Dbeneficiary, Dwinner, DstartTime, DendTime = raffle.GetRaffleInfo(1)
    print(raffle.GetRaffleTicketInfo(1))
    assert Dwinner == smart_get_account(1).address

def test_correctly_pick_winner_random():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 2, {'from': smart_get_account(2), 'value': ticketPrice*2})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 5, {'from': smart_get_account(3), 'value': ticketPrice*5})
    enterTx.wait(1)
    # Now we trigger the end of the raffle
    time.sleep(length)
    fund_link(raffle.address, account=smart_get_account(0))
    claimTx = raffle.ClaimRaffle(1, {'from': smart_get_account(0)})
    claimTx.wait(1)
    requestId = claimTx.events['RequestRandomness']['requestId']
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        value = randint(0,100000)
        fake_VRF_response(raffle,requestId, value)
    # Assert
    Dname, Dbeneficiary, Dwinner, DstartTime, DendTime = raffle.GetRaffleInfo(1)
    assert Dwinner != "0x0000000000000000000000000000000000000000"

# Test that the ticket holders are correclty stored
def test_correctly_store_ticket_holders():
    init_values()
    # Arrange
    raffle = deploy_raffle_contract()
    name = "Test Raffle"
    createTx = raffle.CreateRaffle(name, ticketPrice, length, {'from': smart_get_account(0)})
    createTx.wait(1)
    # Act
    enterTx = raffle.BuyTickets(1, 1, {'from': smart_get_account(1), 'value': ticketPrice})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 2, {'from': smart_get_account(2), 'value': ticketPrice*2})
    enterTx.wait(1)
    enterTx = raffle.BuyTickets(1, 5, {'from': smart_get_account(3), 'value': ticketPrice*5})
    enterTx.wait(1)
    # Assert
    Dname, DstartTime, DendTime, DticketCount, DticketPrice = raffle.GetRaffleTicketInfo(1)
    assert DticketCount == 8
    assert raffle.GetRaffleBalance(1, smart_get_account(1)) == 1
    assert raffle.GetRaffleBalance(1, smart_get_account(2)) == 2
    assert raffle.GetRaffleBalance(1, smart_get_account(3)) == 5