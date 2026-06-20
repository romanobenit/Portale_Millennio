import pytest


@pytest.mark.asyncio
async def test_lista_slot_pubblica(client):
    resp = await client.get("/api/v1/calendario")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_ati_feed_senza_api_key(client):
    resp = await client.get("/api/v1/calendario/ati-feed")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ati_feed_con_api_key_errata(client):
    resp = await client.get(
        "/api/v1/calendario/ati-feed",
        headers={"x-api-key": "chiave-sbagliata"},
    )
    assert resp.status_code == 401
