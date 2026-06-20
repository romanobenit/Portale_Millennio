from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_crea_socio_senza_auth(client, socio_data):
    resp = await client.post("/api/v1/soci", json=socio_data)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_crea_socio_con_staff_auth(client, socio_data):
    staff_user = {
        "sub": "staff-123",
        "realm_access": {"roles": ["staff"]},
    }
    with patch("core.security.decode_token", new=AsyncMock(return_value=staff_user)):
        resp = await client.post(
            "/api/v1/soci",
            json=socio_data,
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == socio_data["nome"]
    assert data["email"] == socio_data["email"]
    assert "codice_fiscale" in data


@pytest.mark.asyncio
async def test_crea_socio_duplicato_cf(client, socio_data):
    staff_user = {
        "sub": "staff-456",
        "realm_access": {"roles": ["staff"]},
    }
    with patch("core.security.decode_token", new=AsyncMock(return_value=staff_user)):
        await client.post(
            "/api/v1/soci",
            json=socio_data,
            headers={"Authorization": "Bearer fake-token"},
        )
        resp = await client.post(
            "/api/v1/soci",
            json={**socio_data, "email": "altro@test.com"},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_verifica_tessera_pubblica(client):
    import uuid
    # Endpoint pubblico QR: GET /api/v1/tessere/{id}/verifica (CLAUDE.md §M01)
    resp = await client.get(f"/api/v1/tessere/{uuid.uuid4()}/verifica")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lista_tessere_socio(client):
    import uuid
    staff_user = {"sub": "staff-789", "realm_access": {"roles": ["staff"]}}
    with patch("core.security.decode_token", new=AsyncMock(return_value=staff_user)):
        resp = await client.get(
            f"/api/v1/soci/{uuid.uuid4()}/tessere",
            headers={"Authorization": "Bearer fake-token"},
        )
    # socio inesistente → lista vuota (non 404, perché non controlliamo l'esistenza del socio nella lista)
    assert resp.status_code == 200
    assert resp.json() == []
