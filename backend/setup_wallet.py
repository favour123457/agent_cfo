import os
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

def generate_wallet():
    # Only generate if it doesn't exist
    if os.path.exists(".env"):
        load_dotenv(".env")
        if os.getenv("ASP_PRIVATE_KEY"):
            print(f"Wallet already exists in .env")
            print(f"Address: {Account.from_key(os.getenv('ASP_PRIVATE_KEY')).address}")
            return

    acct = Account.create()
    with open(".env", "a") as f:
        f.write(f"\nASP_PRIVATE_KEY={acct.key.hex()}\n")
        f.write("OPENAI_API_KEY=your_openai_api_key_here\n")
        f.write("CONTRACT_ADDRESS=\n")
    
    print("=========================================")
    print("NEW WALLET GENERATED FOR ASP ARBITER")
    print(f"Address: {acct.address}")
    print("Private Key saved to backend/.env")
    print("=========================================")
    print("\nACTION REQUIRED: Please go to https://www.okx.com/xlayer/faucet")
    print(f"and request testnet OKB for {acct.address} so we can deploy the contract.")

if __name__ == "__main__":
    generate_wallet()
