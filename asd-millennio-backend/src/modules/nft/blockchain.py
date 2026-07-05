import asyncio
from contextlib import asynccontextmanager

from eth_account import Account
from web3 import AsyncWeb3, Web3
from web3.middleware import ExtraDataToPOAMiddleware

from core.config import get_settings
from core.logger import logger
from modules.nft.wallet import get_account_from_encrypted

settings = get_settings()

PALASIRIO_NFT_ABI = [
    {
        "inputs": [{"name": "to", "type": "address"}, {"name": "tokenURI", "type": "string"}],
        "name": "mintNFT",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "uri", "type": "string"},
            {"name": "slotKeys", "type": "string[]"},
            {"name": "icalHash", "type": "string"},
        ],
        "name": "mintNFTWithSlots",
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
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "getTokenSlotKeys",
        "outputs": [{"name": "", "type": "string[]"}],
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


@asynccontextmanager
async def _web3():
    """
    Context manager per AsyncWeb3: chiude la sessione aiohttp del provider all'uscita
    (evita "Unclosed client session", soprattutto col worker che usa asyncio.run per task).
    """
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(settings.polygon_rpc_url))
    # In web3.py, usare .add() — inject(layer=0) è stato rimosso
    w3.middleware_onion.add(ExtraDataToPOAMiddleware)
    try:
        yield w3
    finally:
        try:
            await w3.provider.disconnect()
        except Exception:  # noqa: BLE001 — chiusura best-effort
            pass


def _contract(w3: AsyncWeb3):
    return w3.eth.contract(
        address=Web3.to_checksum_address(settings.contract_address_palasirio_nft),
        abi=PALASIRIO_NFT_ABI,
    )


def _extract_token_id_from_receipt(receipt) -> int:
    """
    Estrae il tokenId dall'evento Transfer del receipt.
    Più sicuro di getTokensByOwner[-1], vulnerabile a race condition con mint concorrenti.
    """
    transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex()
    for log_entry in receipt.logs:
        if (
            log_entry["address"].lower() == settings.contract_address_palasirio_nft.lower()
            and len(log_entry["topics"]) == 4
            and log_entry["topics"][0].hex() == transfer_topic
        ):
            return int(log_entry["topics"][3].hex(), 16)
    raise RuntimeError("Token ID non trovato nei log della transazione")


async def mint_nft(recipient_address: str, token_uri: str, minter_encrypted_key: str) -> int:
    """Minta un NFT (versione semplice, senza slot) e restituisce il token_id."""
    async with _web3() as w3:
        # AES decrypt è CPU-bound — thread separato
        minter = await asyncio.to_thread(get_account_from_encrypted, minter_encrypted_key)
        contract = _contract(w3)

        # 'pending' include le tx non ancora minate: evita riuso dello stesso nonce
        nonce = await w3.eth.get_transaction_count(minter.address, "pending")
        gas_price = await w3.eth.gas_price

        mint_fn = contract.functions.mintNFT(
            Web3.to_checksum_address(recipient_address), token_uri
        )
        try:
            estimated_gas = await mint_fn.estimate_gas({"from": minter.address})
            gas_limit = int(estimated_gas * 1.2)  # 20% di margine
        except Exception as gas_err:
            logger.warning("Gas estimation fallita, uso fallback 300000: %s", gas_err)
            gas_limit = 300_000

        tx = await mint_fn.build_transaction({
            "from": minter.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": gas_limit,
            "chainId": settings.polygon_chain_id,
        })
        signed = await asyncio.to_thread(minter.sign_transaction, tx)
        tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status != 1:
            raise RuntimeError(f"Transazione fallita: {tx_hash.hex()}")

        token_id = _extract_token_id_from_receipt(receipt)
        logger.info("Token ID estratto dall'evento Transfer: %d", token_id)
        return token_id


async def mint_nft_with_slots(
    recipient_address: str,
    token_uri: str,
    slot_keys: list[str],
    ical_hash: str,
) -> int:
    """
    Minta un NFT prenotando PIÙ slot per-ora (anti double-sell on-chain).
    Firmata dal MINTER del contratto (owner ASD, chiave RAW come update_token_uri),
    NON dal wallet del socio che non è autorizzato a mintare; il token è emesso
    verso il wallet custodiale del socio. Reverta on-chain se un slotKey è già preso.
    """
    async with _web3() as w3:
        minter = Account.from_key(settings.minter_private_key)
        contract = _contract(w3)

        nonce = await w3.eth.get_transaction_count(minter.address, "pending")
        gas_price = await w3.eth.gas_price

        mint_fn = contract.functions.mintNFTWithSlots(
            Web3.to_checksum_address(recipient_address), token_uri, slot_keys, ical_hash
        )
        try:
            estimated_gas = await mint_fn.estimate_gas({"from": minter.address})
            gas_limit = int(estimated_gas * 1.2)
        except Exception as gas_err:
            logger.warning("Gas estimation fallita (mintNFTWithSlots), fallback: %s", gas_err)
            gas_limit = 250_000 + 70_000 * max(1, len(slot_keys))

        tx = await mint_fn.build_transaction({
            "from": minter.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": gas_limit,
            "chainId": settings.polygon_chain_id,
        })
        signed = await asyncio.to_thread(minter.sign_transaction, tx)
        tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status != 1:
            raise RuntimeError(f"Transazione mintNFTWithSlots fallita: {tx_hash.hex()}")

        token_id = _extract_token_id_from_receipt(receipt)
        logger.info("Token ID (mintWithSlots) estratto: %d, slot=%d", token_id, len(slot_keys))
        return token_id


async def update_token_uri(token_id: int, new_uri: str, new_ical_hash: str) -> None:
    """Aggiorna l'URI IPFS e l'hash iCal on-chain dopo il mint (PRD flusso 14-step).
    Chiamata dopo aver rigenerato i metadati con il token_id reale."""
    async with _web3() as w3:
        # minter_private_key è una chiave hex RAW (non cifrata con AES), a differenza
        # delle chiavi dei wallet soci che passano per get_account_from_encrypted.
        minter = Account.from_key(settings.minter_private_key)
        contract = _contract(w3)

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


async def is_slot_booked(slot_key: str) -> bool:
    """View on-chain: lo slotKey è già prenotato? (read-only)."""
    async with _web3() as w3:
        return bool(await _contract(w3).functions.isSlotBooked(slot_key).call())


async def find_token_by_slots(owner_address: str, slot_keys: list[str]) -> int | None:
    """
    Recupero orfano: trova il token dell'owner i cui slotKey coincidono esattamente
    con quelli dati. Usato quando il mint on-chain è avvenuto ma il checkpoint DB no.
    """
    target = set(slot_keys)
    async with _web3() as w3:
        contract = _contract(w3)
        tokens = list(await contract.functions.getTokensByOwner(
            Web3.to_checksum_address(owner_address)
        ).call())
        for tid in tokens:
            keys = set(await contract.functions.getTokenSlotKeys(int(tid)).call())
            if keys == target:
                return int(tid)
    return None


async def get_tokens_by_owner(owner_address: str) -> list[int]:
    async with _web3() as w3:
        tokens = await _contract(w3).functions.getTokensByOwner(
            Web3.to_checksum_address(owner_address)
        ).call()
        return list(tokens)
