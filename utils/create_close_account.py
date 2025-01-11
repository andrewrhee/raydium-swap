# create_close_account.py

from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
    initialize_account,
)
from solders.pubkey import Pubkey
from solders.instruction import Instruction
from solana.rpc.types import TokenAccountOpts
from solders.instruction import AccountMeta
from construct import Struct, Int64ul, Bytes
import json
import requests
import hashlib

# Constants
LAMPORTS_PER_SOL = 1000000000
AMM_PROGRAM_ID = Pubkey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
SERUM_PROGRAM_ID = Pubkey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")

# Set the SPL Token Program ID to the Default SPL Token Program
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

# Define the Swap Instruction Layout with an 8-byte discriminator
SWAP_LAYOUT = Struct(
    "instruction" / Bytes(8),  # 8-byte discriminator
    "amount_in" / Int64ul,  # 8-byte unsigned little-endian integer
    "min_amount_out" / Int64ul,  # 8-byte unsigned little-endian integer
)


def get_discriminator(instruction_name: str) -> bytes:
    """
    Generates an 8-byte discriminator for the given instruction name.
    """
    hash = hashlib.sha256(instruction_name.encode()).digest()
    return hash[:8]


# def make_swap_instruction(
#     amount_in: int,
#     token_account_in: Pubkey,
#     token_account_out: Pubkey,
#     accounts: dict,
#     mint: Pubkey,
#     ctx,
#     owner,
# ) -> Instruction:
#     """
#     Creates a swap instruction for the Raydium Liquidity Pool V4.

#     Args:
#         amount_in (int): The amount of tokens to swap.
#         token_account_in (Pubkey): The user's source token account.
#         token_account_out (Pubkey): The user's destination token account.
#         accounts (dict): A dictionary containing necessary account public keys.
#         mint (Pubkey): The mint address of the token being swapped.
#         ctx: The Solana client context.
#         owner: The owner's keypair.

#     Returns:
#         Instruction: The constructed swap instruction.
#     """

#     # Define the accounts first
#     keys = [
#         AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
#         AccountMeta(pubkey=accounts["amm_id"], is_signer=False, is_writable=True),
#         AccountMeta(pubkey=accounts["authority"], is_signer=False, is_writable=False),
#         AccountMeta(pubkey=accounts["open_orders"], is_signer=False, is_writable=True),
#         AccountMeta(
#             pubkey=accounts["target_orders"], is_signer=False, is_writable=True
#         ),
#         AccountMeta(pubkey=accounts["base_vault"], is_signer=False, is_writable=True),
#         AccountMeta(pubkey=accounts["quote_vault"], is_signer=False, is_writable=True),
#         AccountMeta(pubkey=SERUM_PROGRAM_ID, is_signer=False, is_writable=False),
#         AccountMeta(pubkey=accounts["market_id"], is_signer=False, is_writable=True),
#         AccountMeta(pubkey=accounts["bids"], is_signer=False, is_writable=True),
#         AccountMeta(pubkey=accounts["asks"], is_signer=False, is_writable=True),
#         AccountMeta(pubkey=accounts["event_queue"], is_signer=False, is_writable=True),
#         AccountMeta(
#             pubkey=accounts["market_base_vault"], is_signer=False, is_writable=True
#         ),
#         AccountMeta(
#             pubkey=accounts["market_quote_vault"], is_signer=False, is_writable=True
#         ),
#         AccountMeta(
#             pubkey=accounts["market_authority"], is_signer=False, is_writable=False
#         ),
#         AccountMeta(
#             pubkey=token_account_in, is_signer=False, is_writable=True
#         ),  # UserSourceTokenAccount
#         AccountMeta(
#             pubkey=token_account_out, is_signer=False, is_writable=True
#         ),  # UserDestTokenAccount
#         AccountMeta(
#             pubkey=owner.pubkey(), is_signer=True, is_writable=False
#         ),  # UserOwner
#     ]

#     # Build the instruction data with the correct discriminator
#     discriminator = get_discriminator("swapBaseIn")

#     data = SWAP_LAYOUT.build(
#         {
#             "instruction": discriminator,
#             "amount_in": amount_in,
#             "min_amount_out": 1,  # Set to a small non-zero value
#         }
#     )

#     # Log the instruction data and involved accounts for debugging
#     print("Swap Instruction Data:", data.hex())
#     print("Accounts Involved in Swap Instruction:", [str(meta.pubkey) for meta in keys])

#     # Create and return the Instruction object
#     return Instruction(AMM_PROGRAM_ID, data, keys)


def make_swap_instruction(
    amount_in: int,
    token_account_in: Pubkey,
    token_account_out: Pubkey,
    accounts: dict,
    mint: Pubkey,
    ctx,
    owner,
) -> Instruction:
    """
    Creates a swap instruction for the Raydium Liquidity Pool V4.
    """
    # Define the accounts
    keys = [
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=accounts["amm_id"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["authority"], is_signer=False, is_writable=False),
        AccountMeta(pubkey=accounts["open_orders"], is_signer=False, is_writable=True),
        AccountMeta(
            pubkey=accounts["target_orders"], is_signer=False, is_writable=True
        ),
        AccountMeta(pubkey=accounts["base_vault"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["quote_vault"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=SERUM_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=accounts["market_id"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["bids"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["asks"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["event_queue"], is_signer=False, is_writable=True),
        AccountMeta(
            pubkey=accounts["market_base_vault"], is_signer=False, is_writable=True
        ),
        AccountMeta(
            pubkey=accounts["market_quote_vault"], is_signer=False, is_writable=True
        ),
        AccountMeta(
            pubkey=accounts["market_authority"], is_signer=False, is_writable=False
        ),
        AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),
        AccountMeta(pubkey=token_account_out, is_signer=False, is_writable=True),
        AccountMeta(pubkey=owner.pubkey(), is_signer=True, is_writable=False),
    ]

    # Build the instruction data with correct format for Raydium V4
    # Instruction layout:
    # - u8: instruction type (9 for swapBaseIn)
    # - u64: amount_in
    # - u64: minimum_amount_out
    data = bytes([9]) + amount_in.to_bytes(8, "little") + (1).to_bytes(8, "little")

    # Log for debugging
    print(f"Swap Instruction Data: {data.hex()}")
    print("Accounts Involved in Swap Instruction:", [str(meta.pubkey) for meta in keys])

    return Instruction(AMM_PROGRAM_ID, data, keys)


def get_token_account(ctx, owner: Pubkey, mint: Pubkey):
    """
    Retrieves the token account for a given owner and mint. If it doesn't exist, prepares instructions to create it.
    """
    try:
        account_data = ctx.get_token_accounts_by_owner(owner, TokenAccountOpts(mint))
        if account_data.value:
            print(f"Existing Token Account Found: {account_data.value[0].pubkey}")
            return account_data.value[0].pubkey, None
        else:
            raise Exception("No token account found.")
    except Exception as e:
        print(
            f"Token account not found. Preparing to create associated token account. Error: {e}"
        )
        swap_associated_token_address = get_associated_token_address(owner, mint)
        # Create ATA without setting immutableOwner using default parameters
        swap_token_account_Instructions = create_associated_token_account(
            payer=owner, owner=owner, mint=mint
        )
        return swap_associated_token_address, swap_token_account_Instructions


def sell_get_token_account(ctx, owner: Pubkey, mint: Pubkey):
    """
    Retrieves the token account for selling tokens. Prints a message if not found.
    """
    try:
        account_data = ctx.get_token_accounts_by_owner(owner, TokenAccountOpts(mint))
        if account_data.value:
            print(f"Sell Token Account Found: {account_data.value[0].pubkey}")
            return account_data.value[0].pubkey
        else:
            raise Exception("No token account found.")
    except Exception as e:
        print(f"Sell Token account not found. Error: {e}")
        return None


def extract_pool_info(pools_list: list, mint: str) -> dict:
    """
    Extracts pool information for a given mint from a list of pools.
    """
    for pool in pools_list:
        if (
            pool["baseMint"] == mint
            and pool["quoteMint"] == "So11111111111111111111111111111111111111112"
        ):
            return pool
        elif (
            pool["quoteMint"] == mint
            and pool["baseMint"] == "So11111111111111111111111111111111111111112"
        ):
            return pool
    raise Exception(f"{mint} pool not found!")


def fetch_pool_keys(mint: str):
    """
    Fetches and parses pool keys for a given mint. Caches the pools in a JSON file.
    """
    amm_info = {}
    all_pools = {}
    try:
        # Attempt to load cached pools
        with open("all_pools.json", "r") as file:
            all_pools = json.load(file)
        amm_info = extract_pool_info(all_pools, mint)
    except Exception as e:
        print(f"Failed to load cached pools. Fetching from API. Error: {e}")
        # Fetch pools from Raydium API if cache not available
        try:
            resp = requests.get(
                "https://api.raydium.io/v2/sdk/liquidity/mainnet.json", stream=True
            )
            pools = resp.json()
            official = pools.get("official", [])
            unofficial = pools.get("unOfficial", [])
            all_pools = official + unofficial

            # Store all_pools in a JSON file for future use
            with open("all_pools.json", "w") as file:
                json.dump(all_pools, file)
            amm_info = extract_pool_info(all_pools, mint)
        except Exception as ex:
            print(f"Failed to fetch pools from API. Error: {ex}")
            return "failed"

    # Construct and return the pool keys dictionary
    try:
        return {
            "amm_id": Pubkey.from_string(amm_info["id"]),
            "authority": Pubkey.from_string(amm_info["authority"]),
            "base_mint": Pubkey.from_string(amm_info["baseMint"]),
            "base_decimals": amm_info["baseDecimals"],
            "quote_mint": Pubkey.from_string(amm_info["quoteMint"]),
            "quote_decimals": amm_info["quoteDecimals"],
            "lp_mint": Pubkey.from_string(amm_info["lpMint"]),
            "open_orders": Pubkey.from_string(amm_info["openOrders"]),
            "target_orders": Pubkey.from_string(amm_info["targetOrders"]),
            "base_vault": Pubkey.from_string(amm_info["baseVault"]),
            "quote_vault": Pubkey.from_string(amm_info["quoteVault"]),
            "market_id": Pubkey.from_string(amm_info["marketId"]),
            "market_base_vault": Pubkey.from_string(amm_info["marketBaseVault"]),
            "market_quote_vault": Pubkey.from_string(amm_info["marketQuoteVault"]),
            "market_authority": Pubkey.from_string(amm_info["marketAuthority"]),
            "bids": Pubkey.from_string(amm_info["marketBids"]),
            "asks": Pubkey.from_string(amm_info["marketAsks"]),
            "event_queue": Pubkey.from_string(amm_info["marketEventQueue"]),
        }
    except Exception as e:
        print(f"Failed to construct pool keys. Error: {e}")
        return "failed"
