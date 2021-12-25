from brownie import network, accounts, config, Contract, VRFCoordinatorMock, LinkToken, interface
from brownie.network import contract

LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development","ganache-local"]
FORKED = ["mainnet-fork","mainnet-fork-dev"]

def get_account(index = 0, id = None): # Automaticaly gets a good account
    if id != None:
        return accounts.load(id)
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS or network.show_active() in FORKED:
        return accounts[index]
    return accounts.add(config["wallets"]["from_key"])

contract_to_mock = {
 "vrf_coordinator": VRFCoordinatorMock,
 "link_token": LinkToken
}

def deploy_mocks():
    account = get_account()
    link_token = LinkToken.deploy({"from": account})
    VRFCoordinatorMock.deploy(link_token.address, {"from": account})
    print("Mocks deployed")

# A function that gets a contract from the brownie config and deploy mocks if needed
def get_contract(contract_name):
    contract_type = contract_to_mock[contract_name]
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        if len(contract_type) <= 0:
            deploy_mocks()
        contract = contract_type[-1] # Last contract
    else:
        contract_address = config["networks"][network.show_active()][contract_name]
        contract = Contract.from_abi(contract_type._name, contract_address, contract_type.abi)
    return contract 

def fund_link(contract_address, account = None, link = None, amount = 0.1*10**18):
    account = account if account else get_account(id="test1")
    link = link if link else get_contract("link_token")
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS: link.fund({'from': account}) # Gime link
    print("link:", link, "balance", link.balanceOf(account))
    # tx = link.transfer(contract_address, amount, {"from": account}) # Cringe way using a transaction
    link_contract = interface.LinkTokenInterface(link.address)
    tx = link_contract.transfer(contract_address, amount, {"from": account}) # Using the interface
    tx.wait(1)
    print("Funded link")
    return tx