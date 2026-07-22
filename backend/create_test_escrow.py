import os
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from dotenv import load_dotenv

load_dotenv()

w3 = Web3(Web3.HTTPProvider("https://testrpc.xlayer.tech"))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

private_key = os.getenv("ASP_PRIVATE_KEY")
acct = w3.eth.account.from_key(private_key)
contract_address = os.getenv("CONTRACT_ADDRESS")

escrow_abi = [
    {
        "inputs": [
            {"internalType": "address", "name": "_payee", "type": "address"},
            {"internalType": "address", "name": "_arbiter", "type": "address"},
            {"internalType": "string", "name": "_taskDescription", "type": "string"}
        ],
        "name": "createEscrow",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "nextEscrowId",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

contract = w3.eth.contract(address=contract_address, abi=escrow_abi)

def create_escrow():
    print("Creating Test Escrow on X Layer...")
    nonce = w3.eth.get_transaction_count(acct.address)
    
    # We set ourselves as the payer, arbiter, and a dummy address as payee just for this test
    payee = "0x0000000000000000000000000000000000000B0b"
    arbiter = acct.address
    task_desc = "Fetch https://api.coingecko.com/api/v3/simple/price?ids=okb&vs_currencies=usd and report the current USD price of OKB."
    amount = w3.to_wei(0.0001, 'ether') # 0.0001 OKB
    
    tx = contract.functions.createEscrow(payee, arbiter, task_desc).build_transaction({
        'from': acct.address,
        'value': amount,
        'nonce': nonce,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction sent! Hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block {receipt.blockNumber}")
    current_id = contract.functions.nextEscrowId().call() - 1
    print(f"Test Escrow ID {current_id} created successfully!")

if __name__ == "__main__":
    create_escrow()
