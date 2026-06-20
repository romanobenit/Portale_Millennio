import os
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_genera_wallet_cifra_decifra():
    fake_key = os.urandom(32).hex()
    with patch("modules.nft.wallet.settings") as mock_settings:
        mock_settings.wallet_encryption_key = fake_key
        from modules.nft.wallet import genera_wallet, _decifra_chiave

        address, encrypted = genera_wallet()

        assert address.startswith("0x")
        assert len(address) == 42
        assert encrypted != ""

        decrypted = _decifra_chiave(encrypted)
        # La chiave privata raw è 64 char hex (senza prefisso 0x)
        assert len(decrypted) == 64


def test_genera_wallet_address_unico():
    import os
    from unittest.mock import patch
    fake_key = os.urandom(32).hex()
    with patch("modules.nft.wallet.settings") as mock_settings:
        mock_settings.wallet_encryption_key = fake_key
        from modules.nft.wallet import genera_wallet
        addr1, _ = genera_wallet()
        addr2, _ = genera_wallet()
        assert addr1 != addr2
