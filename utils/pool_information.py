# utils/pool_information.py

import json
import requests
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import MemcmpOpts
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
import os
from dotenv import load_dotenv
import time

from utils.layouts import AMM_INFO_LAYOUT_V4_1, MARKET_LAYOUT, get_offset

# Load .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

RPC_HTTPS_URL = os.getenv("RPC_HTTPS_URL")

WSOL = Pubkey.from_string("So11111111111111111111111111111111111111112")
ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string(
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
)

MINT_LEN: int = 82
ACCOUNT_LEN: int = 165
MULTISIG_LEN: int = 355

TOKEN_PROGRAM_ID: Pubkey = Pubkey.from_string(
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
)
TOKEN_PROGRAM_ID_2022: Pubkey = Pubkey.from_string(
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
)

RAY_V4 = Pubkey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
PUMP_FUN_PROGRAM = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
PUMP_LIQUIDITY_MIGRATOR = Pubkey.from_string(
    "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"
)

RAY_AUTHORITY_V4 = Pubkey.from_string("5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1")

OPEN_BOOK_PROGRAM = Pubkey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")

offset_base_mint = get_offset(AMM_INFO_LAYOUT_V4_1, "coinMintAddress")
offset_quote_mint = get_offset(AMM_INFO_LAYOUT_V4_1, "pcMintAddress")

LAMPORTS_PER_SOL = 1000000000


def is_solana_address_pump(address):
    address = str(address)
    """
    Check if the given Solana address ends with 'pump'.

    :param address: The Solana address string to check.
    :return: True if the address ends with 'pump', False otherwise.
    """

    return address.endswith("pump")


async def getpoolIdByMint(mint, ctx):
    start_time = time.time()
    pump_token = is_solana_address_pump(str(mint))
    print(pump_token)
    if pump_token:
        memcmp_opts_base = MemcmpOpts(offset=432, bytes=str(mint))
    else:
        memcmp_opts_base = MemcmpOpts(offset=400, bytes=str(mint))
    filters_tokens = [memcmp_opts_base]

    while True:
        try:
            if time.time() - start_time > 5:
                return False

            poolids = (
                await ctx.get_program_accounts(
                    pubkey=RAY_V4,
                    commitment=Confirmed,
                    encoding="jsonParsed",
                    filters=filters_tokens,
                )
            ).value
            break
        except:
            pass
    if len(poolids) > 0:
        return poolids[0].pubkey
    else:
        return None


async def gen_pool(amm_id, ctx):

    try:
        amm_id = Pubkey.from_string(amm_id)
        ctx = AsyncClient(RPC_HTTPS_URL, commitment=Confirmed)

        start = time.time()
        while True:
            try:
                amm_data = (await ctx.get_account_info_json_parsed(amm_id)).value.data
                break
            except:
                if (time.time() - start) > 3:
                    return {
                        "error": "server timeout - took too long to find the pool info"
                    }
                pass

        amm_data_decoded = AMM_INFO_LAYOUT_V4_1.parse(amm_data)
        OPEN_BOOK_PROGRAM = Pubkey.from_bytes(amm_data_decoded.serumProgramId)
        marketId = Pubkey.from_bytes(amm_data_decoded.serumMarket)
        # print("Market --- ", marketId))
        try:
            while True:
                try:
                    marketInfo = (
                        await ctx.get_account_info_json_parsed(marketId)
                    ).value.data
                    break
                except:
                    if (time.time() - start) > 3:
                        return {
                            "error": "server timeout - took too long to find the pool info"
                        }
                    pass

            market_decoded = MARKET_LAYOUT.parse(marketInfo)

            pool_keys = {
                "amm_id": amm_id,
                "base_mint": Pubkey.from_bytes(market_decoded.base_mint),
                "quote_mint": Pubkey.from_bytes(market_decoded.quote_mint),
                "lp_mint": Pubkey.from_bytes(amm_data_decoded.lpMintAddress),
                "version": 4,
                "base_decimals": amm_data_decoded.coinDecimals,
                "quote_decimals": amm_data_decoded.pcDecimals,
                "lpDecimals": amm_data_decoded.coinDecimals,
                "programId": RAY_V4,
                "authority": RAY_AUTHORITY_V4,
                "open_orders": Pubkey.from_bytes(amm_data_decoded.ammOpenOrders),
                "target_orders": Pubkey.from_bytes(amm_data_decoded.ammTargetOrders),
                "base_vault": Pubkey.from_bytes(amm_data_decoded.poolCoinTokenAccount),
                "quote_vault": Pubkey.from_bytes(amm_data_decoded.poolPcTokenAccount),
                "withdrawQueue": Pubkey.from_bytes(amm_data_decoded.poolWithdrawQueue),
                "lpVault": Pubkey.from_bytes(amm_data_decoded.poolTempLpTokenAccount),
                "marketProgramId": OPEN_BOOK_PROGRAM,
                "market_id": marketId,
                "market_authority": Pubkey.create_program_address(
                    [bytes(marketId)]
                    + [bytes([market_decoded.vault_signer_nonce])]
                    + [bytes(7)],
                    OPEN_BOOK_PROGRAM,
                ),
                "market_base_vault": Pubkey.from_bytes(market_decoded.base_vault),
                "market_quote_vault": Pubkey.from_bytes(market_decoded.quote_vault),
                "bids": Pubkey.from_bytes(market_decoded.bids),
                "asks": Pubkey.from_bytes(market_decoded.asks),
                "event_queue": Pubkey.from_bytes(market_decoded.event_queue),
                "pool_open_time": amm_data_decoded.poolOpenTime,
            }

            Buy_keys = [
                "amm_id",
                "authority",
                "base_mint",
                "base_decimals",
                "quote_mint",
                "quote_decimals",
                "lp_mint",
                "open_orders",
                "target_orders",
                "base_vault",
                "quote_vault",
                "market_id",
                "market_base_vault",
                "market_quote_vault",
                "market_authority",
                "bids",
                "asks",
                "event_queue",
            ]

            transactionkeys = {key: pool_keys[key] for key in Buy_keys}

            return transactionkeys

        except:
            {"error": "unexpected error occured"}
    except:
        return {"error": "incorrect pair address"}


async def fetch_pool_keys(mint: str):
    """
    Fetches and parses pool keys for a given mint. Caches the pools in a JSON file.

    Args:
        mint (str): The mint address to search for.

    Returns:
        dict or str: A dictionary of pool keys if found, else "failed".
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


def extract_pool_info(pools_list: list, mint: str) -> dict:
    """
    Extracts pool information for a given mint from a list of pools.

    Args:
        pools_list (list): List of pool dictionaries.
        mint (str): The mint address to search for.

    Returns:
        dict: The pool information dictionary.

    Raises:
        Exception: If the pool is not found.
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
