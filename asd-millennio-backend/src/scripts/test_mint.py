"""
Script di test manuale per il mint NFT su Polygon Amoy.
Usa la chiave minter dal .env, minta un NFT di prova verso se stesso
e verifica il token ID risultante on-chain.

Uso:
  cd asd-millennio-backend
  python src/scripts/test_mint.py
"""
import asyncio
import sys

sys.path.insert(0, "src")

from core.config import get_settings
from modules.nft.blockchain import get_tokens_by_owner, mint_nft
from modules.nft.wallet import _cifra_chiave as cifra_chiave

settings = get_settings()


async def main():
    print("=" * 60)
    print("  TEST MINT — PalasirionNFT su Polygon Amoy")
    print("=" * 60)
    print(f"  RPC:       {settings.polygon_rpc_url[:50]}...")
    print(f"  Chain ID:  {settings.polygon_chain_id}")
    print(f"  Contratto: {settings.contract_address_palasirion_nft}")
    print()

    # Usa la chiave minter dal .env cifrandola al volo per il test
    # (in produzione la chiave è già cifrata nel DB wallet)
    if not settings.minter_private_key:
        print("❌ MINTER_PRIVATE_KEY non impostata nel .env")
        return
    if not settings.wallet_encryption_key:
        print("❌ WALLET_ENCRYPTION_KEY non impostata nel .env")
        return
    if not settings.contract_address_palasirion_nft:
        print("❌ CONTRACT_ADDRESS_PALASIRION_NFT non impostata nel .env")
        return

    # Cifra la chiave minter con la WALLET_ENCRYPTION_KEY (come farebbe il sistema)
    print("  Cifratura chiave minter...")
    encrypted_key = cifra_chiave(settings.minter_private_key.lstrip("0x"))

    # Recipient = il wallet minter stesso (per il test)
    from eth_account import Account
    minter_account = Account.from_key(settings.minter_private_key)
    recipient = minter_account.address
    print(f"  Recipient: {recipient}")

    # URI di test (normalmente punta a IPFS)
    test_uri = "ipfs://QmTestMillennioASDPalasirionNFT000000000000001"

    print()
    print("  Invio transazione mint...")
    try:
        token_id = await mint_nft(recipient, test_uri, encrypted_key)
        print(f"  OK Mint riuscito! Token ID: {token_id}")
        print()
        print(f"  Verifica su Polygonscan:")
        print(f"  https://amoy.polygonscan.com/token/{settings.contract_address_palasirion_nft}?a={recipient}")
        print()

        # Verifica che il token sia nel wallet
        tokens = await get_tokens_by_owner(recipient)
        print(f"  Token nel wallet {recipient[:10]}...:")
        print(f"  {tokens}")

    except Exception as e:
        print(f"  ERRORE: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
