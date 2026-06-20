import asyncio
import json

from eth_account import Account
from web3 import AsyncWeb3, Web3
from web3.middleware import ExtraDataToPOAMiddleware

from core.config import get_settings
from core.logger import logger
from modules.nft.wallet import get_account_from_encrypted

settings = get_settings()

PALASIRION_NFT_ABI = [
    {
        "inputs": [{"name": "to", "type": "address"}, {"name": "tokenURI", "type": "string"}],
        "name": "mintNFT",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}, {"name": "newUri", "type": "string"}],
        "name": "updateTokenURI",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}, {"name": "newIcalHash", "type": "string"}],
        "name": "updateIcalHash",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "getTokensByOwner",
        "outputs": [{"name": "", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "slotKey", "type": "string"}],
        "name": "isSlotBooked",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "tokenId", "type": "uint256"},
            {"indexed": True, "name": "member", "type": "address"},
            {"indexed": False, "name": "icalHash", "type": "string"},
            {"indexed": False, "name": "slotKey", "type": "string"},
        ],
        "name": "SlotBooked",
        "type": "event",
    },
]


def _get_web3() -> AsyncWeb3:
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(settings.polygon_rpc_url))
    # In web3.py v6, usare .add() — inject(layer=0) è stato rimosso
    w3.middleware_onion.add(ExtraDataToPOAMiddleware)
    return w3


async def mint_nft(recipient_address: str, token_uri: str, minter_encrypted_key: str) -> int:
    """Minta un NFT e restituisce il token_id assegnato on-chain."""
    w3 = _get_web3()
    # AES decrypt è CPU-bound — thread separato
    minter = await asyncio.to_thread(get_account_from_encrypted, minter_encrypted_key)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.contract_address_palasirion_nft),
        abi=PALASIRION_NFT_ABI,
    )

    # 'pending' include le tx non ancora minate: evita riuso dello stesso nonce
    nonce = await w3.eth.get_transaction_count(minter.address, "pending")
    gas_price = await w3.eth.gas_price

    mint_fn = contract.functions.mintNFT(
        Web3.to_checksum_address(recipient_address), token_uri
    )
    # Stima gas esplicita: evita fallimenti on-chain per insufficient gas
    try:
        estimated_gas = await mint_fn.estimate_gas({"from": minter.address})
        gas_limit = int(estimated_gas * 1.2)  # 20% di margine
    except Exception as gas_err:
        logger.warning("Gas estimation fallita, uso fallback 300000: %s", gas_err)
        gas_limit = 300_000

    tx = await mint_fn.build_transaction(
        {
            "from": minter.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": gas_limit,
            "chainId": settings.polygon_chain_id,
        }
    )
    # sign_transaction è sincrono (crittografia locale) — thread separato
    signed = await asyncio.to_thread(minter.sign_transaction, tx)

    # eth-account v0.11 usa rawTransaction (camelCase) come attributo primario
    tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt.status != 1:
        raise RuntimeError(f"Transazione fallita: {tx_hash.hex()}")

    # Estrae il tokenId dall'evento Transfer emesso nel receipt.
    # Più sicuro di getTokensByOwner[-1] che è vulnerabile a race condition
    # in caso di mint concorrenti allo stesso indirizzo.
    transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex()
    for log_entry in receipt.logs:
        if (
            log_entry["address"].lower() == settings.contract_address_palasirion_nft.lower()
            and len(log_entry["topics"]) == 4
            and log_entry["topics"][0].hex() == transfer_topic
        ):
            token_id = int(log_entry["topics"][3].hex(), 16)
            logger.info("Token ID estratto dall'evento Transfer: %d", token_id)
            return token_id

    raise RuntimeError(f"Token ID non trovato nei log della transazione {tx_hash.hex()}")


async def update_token_uri(token_id: int, new_uri: str, new_ical_hash: str) -> None:
    """Aggiorna l'URI IPFS e l'hash iCal on-chain dopo il mint (PRD flusso 14-step).
    Chiamata dopo aver rigenerato i metadati con il token_id reale."""
    w3 = _get_web3()
    minter_key = settings.minter_private_key
    # minter_private_key è una chiave hex RAW (non cifrata con AES), a differenza
    # delle chiavi dei wallet soci che passano per get_account_from_encrypted.
    minter = Account.from_key(minter_key)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.contract_address_palasirion_nft),
        abi=PALASIRION_NFT_ABI,
    )
    # 'pending' include le tx non ancora minate: evita riuso dello stesso nonce
    nonce = await w3.eth.get_transaction_count(minter.address, "pending")
    gas_price = await w3.eth.gas_price

    for fn_name, arg in [("updateTokenURI", new_uri), ("updateIcalHash", new_ical_hash)]:
        fn = getattr(contract.functions, fn_name)(token_id, arg)
        try:
            gas = int((await fn.estimate_gas({"from": minter.address})) * 1.2)
        except Exception:
            gas = 100_000
        tx = await fn.build_transaction({
            "from": minter.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": gas,
            "chainId": settings.polygon_chain_id,
        })
        signed = await asyncio.to_thread(minter.sign_transaction, tx)
        tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if receipt.status != 1:
            raise RuntimeError(f"{fn_name} fallita per token {token_id}: {tx_hash.hex()}")
        nonce += 1  # incrementa nonce per la seconda tx nella stessa sessione

    logger.info("tokenURI e icalHash aggiornati on-chain per token %d", token_id)


async def get_tokens_by_owner(owner_address: str) -> list[int]:
    w3 = _get_web3()
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.contract_address_palasirion_nft),
        abi=PALASIRION_NFT_ABI,
    )
    return list(await contract.functions.getTokensByOwner(
        Web3.to_checksum_address(owner_address)
    ).call())
