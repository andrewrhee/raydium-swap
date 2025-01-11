# buy_wrap_sol.py

import asyncio
import datetime
import time
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.pubkey import Pubkey
from solana.rpc.commitment import Confirmed
from solana.rpc.api import RPCException
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit

from utils.create_close_account import get_token_account, make_swap_instruction
from utils.birdeye import getSymbol
from solana.rpc.async_api import AsyncClient
from utils.pool_information import gen_pool, getpoolIdByMint, fetch_pool_keys
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# Configuration
RPC_HTTPS_URL = os.getenv("RPC_HTTPS_URL")
solana_client = Client(RPC_HTTPS_URL)  # Synchronous client
async_solana_client = AsyncClient(RPC_HTTPS_URL)  # Asynchronous client

# Payer Keypair
payer = Keypair.from_base58_string(os.getenv("PrivateKey"))
Wsol_TokenAccount = os.getenv("WSOL_TokenAccount")

# Constants
AMM_PROGRAM_ID = Pubkey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
SERUM_PROGRAM_ID = Pubkey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")
LAMPORTS_PER_SOL = 1000000000
MAX_RETRIES = 2
RETRY_DELAY = 3


class style:
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"


def getTimestamp():
    return "[" + datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3] + "]"


async def buy(solana_client, TOKEN_TO_SWAP_BUY, payer, amount):

    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            # Re-init transaction preparation
            token_symbol, Sol_Symbol = getSymbol(TOKEN_TO_SWAP_BUY)
            mint = Pubkey.from_string(TOKEN_TO_SWAP_BUY)

            try:
                print("Fetching pool keys...")

                tokenPool_ID = await getpoolIdByMint(
                    mint, AsyncClient(RPC_HTTPS_URL, commitment=Confirmed)
                )
                print("Pool ID:", tokenPool_ID)
                if tokenPool_ID:
                    print("AMM ID FOUND")

                    fetch_pool_key = await gen_pool(
                        str(tokenPool_ID),
                        AsyncClient(RPC_HTTPS_URL, commitment=Confirmed),
                    )
                    pool_keys = fetch_pool_key
                    print("Pool Keys:", pool_keys)
                else:
                    print(
                        "AMM ID NOT FOUND. SEARCHING WILL BE FETCHING WITH RAYDIUM SDK"
                    )

                    # **Await the fetch_pool_keys function**
                    pool_keys = await fetch_pool_keys(str(mint))
                    if pool_keys == "failed":
                        print("Failed to fetch pool keys.")
                        return False
                    print("Fetched Pool Keys:", pool_keys)
            except Exception as e:
                print(f"Error fetching pool keys: {e}")
                return False

            amount_in = int(amount * LAMPORTS_PER_SOL)
            print(f"Amount In: {amount_in} lamports")

            swap_associated_token_address, swap_token_account_Instructions = (
                get_token_account(solana_client, payer.pubkey(), mint)
            )
            print(f"Swap Associated Token Address: {swap_associated_token_address}")

            swap_tx = []
            WSOL_token_account = Pubkey.from_string(Wsol_TokenAccount)
            instructions_swap = make_swap_instruction(
                amount_in,
                WSOL_token_account,
                swap_associated_token_address,
                pool_keys,
                mint,
                solana_client,
                payer,
            )
            if swap_token_account_Instructions is not None:
                print(
                    "Adding Create Associated Token Account Instruction to Transaction"
                )
                # Assuming create_associated_token_account returns a single Instruction
                swap_tx.append(swap_token_account_Instructions)

            print(
                "Adding Swap Instruction and Compute Budget Instructions to Transaction"
            )
            swap_tx.extend(
                [
                    instructions_swap,
                    set_compute_unit_price(498_750),
                    set_compute_unit_limit(4_000_000),
                ]
            )

            # Execute Transaction
            print("Executing Transaction...")
            latest_blockhash_resp = await async_solana_client.get_latest_blockhash()
            latest_blockhash = latest_blockhash_resp.value.blockhash
            compiled_message = MessageV0.try_compile(
                payer.pubkey(),
                swap_tx,
                [],
                latest_blockhash,
            )
            print("Sending transaction...")
            txn = await async_solana_client.send_transaction(
                txn=VersionedTransaction(compiled_message, [payer]),
                opts=TxOpts(skip_preflight=True),
            )
            print("Transaction Signature:", txn.value)
            txid_string_sig = txn.value
            if txid_string_sig:
                print("Transaction sent")
                print(getTimestamp())
                print(
                    style.RED,
                    f"Transaction Signature Waiting to be confirmed: https://solscan.io/tx/{txid_string_sig}"
                    + style.RESET,
                )
                print("Waiting for Confirmation...")

            # **Use async_solana_client to get block height**
            block_height_resp = await async_solana_client.get_block_height(Confirmed)
            block_height = block_height_resp.value
            print(f"Current Block Height: {block_height}")

            confirmation_resp = await async_solana_client.confirm_transaction(
                txid_string_sig,
                commitment=Confirmed,
                sleep_seconds=0.5,
                last_valid_block_height=block_height + 50,
            )

            if (
                confirmation_resp.value[0].err is None
                and str(confirmation_resp.value[0].confirmation_status)
                == "TransactionConfirmationStatus.Confirmed"
            ):
                print(style.GREEN + "Transaction Confirmed" + style.RESET)
                print(
                    style.GREEN,
                    f"Transaction Signature: https://solscan.io/tx/{txid_string_sig}",
                    style.RESET,
                )
                return True

            else:
                print("Transaction not confirmed")
                return False

        except asyncio.TimeoutError:
            print("Transaction confirmation timed out. Retrying...")
            retry_count += 1
            await asyncio.sleep(RETRY_DELAY)
        except RPCException as e:
            print(f"RPC Error: [{e.args[0].message}]... Retrying...")
            retry_count += 1
            await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"Unhandled exception: {e}. Retrying...")
            retry_count += 1
            await asyncio.sleep(RETRY_DELAY)

    print("Failed to confirm transaction after maximum retries.")
    return False


async def main():
    # Example Token to Buy: Replace with your target token mint address
    token_toBuy = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    print("Payer Public Key:", payer.pubkey())
    success = await buy(solana_client, token_toBuy, payer, 0.00065)
    if success:
        print("Buy Transaction Successful!")
    else:
        print("Buy Transaction Failed.")


if __name__ == "__main__":
    asyncio.run(main())
