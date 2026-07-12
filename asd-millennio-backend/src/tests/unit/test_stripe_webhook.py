"""
Regression test: il webhook Stripe deve funzionare con un evento reale.

Bug riprodotto in UAT (2026-07-11): stripe_handler.py faceva `dict(event)` per
serializzare il payload in WebhookLog — con stripe-python 15.x, stripe.Event
non supporta dict() e solleva KeyError: 0, facendo fallire OGNI webhook con
500 prima ancora di processare il pagamento (nessun acquisto è mai stato
confermato via webhook reale in questo ambiente). Fix: riusa il body grezzo
già letto invece di re-serializzare l'oggetto stripe.Event.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from starlette.requests import Request


def _fake_request(payload_dict: dict) -> Request:
    """Request Starlette reale: il rate limiter (slowapi) rifiuta un MagicMock."""
    body = json.dumps(payload_dict).encode("utf-8")

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/webhooks/stripe",
        "headers": [(b"stripe-signature", b"sig_test")],
        "client": ("127.0.0.1", 12345),
        "query_string": b"",
        "app": MagicMock(state=MagicMock(limiter=MagicMock())),
    }
    return Request(scope, receive)


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None  # nessun webhook già processato
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_webhook_checkout_completed_non_crasha_su_evento_reale():
    """
    Costruisce un vero oggetto stripe.Event (non un mock) — dict(event) su
    questo oggetto riproduce il KeyError: 0 se il bug del payload torna.
    """
    from modules.webhooks.stripe_handler import stripe_webhook

    payload_dict = {
        "id": "evt_test_regressione",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_test_regressione",
            "object": "checkout.session",
            "metadata": {},
            "payment_status": "paid",
        }},
    }
    real_event = stripe.Event.construct_from(payload_dict, "sk_test_x")

    db = _mock_db()

    with patch("modules.webhooks.stripe_handler.stripe.Webhook.construct_event", return_value=real_event), \
         patch("modules.webhooks.stripe_handler.NFTService") as MockNFT:
        MockNFT.return_value.conferma_pagamento = AsyncMock(return_value=None)
        result = await stripe_webhook(_fake_request(payload_dict), db=db)

    assert result == {"status": "ok"}
    # Il payload salvato è il body grezzo, non una serializzazione dell'oggetto Event
    saved_log = db.add.call_args[0][0]
    assert saved_log.event_type == "checkout.session.completed"
    assert json.loads(saved_log.payload)["id"] == "evt_test_regressione"


@pytest.mark.asyncio
async def test_webhook_payment_failed_legge_metadata_reale():
    """
    payment_intent.payment_failed legge acquisto_id da metadata — stesso bug
    potenziale: session/PI.to_dict().get(...) invece di .get() diretto.
    """
    from modules.webhooks.stripe_handler import stripe_webhook

    acquisto_id = "11111111-1111-1111-1111-111111111111"
    payload_dict = {
        "id": "evt_test_pi_failed",
        "object": "event",
        "type": "payment_intent.payment_failed",
        "data": {"object": {
            "id": "pi_test_regressione",
            "object": "payment_intent",
            "metadata": {"acquisto_id": acquisto_id},
        }},
    }
    real_event = stripe.Event.construct_from(payload_dict, "sk_test_x")

    acquisto_mock = MagicMock()
    acquisto_mock.id = acquisto_id
    acquisto_mock.stato = "in_attesa_pagamento"

    db = _mock_db()
    webhook_check = MagicMock()
    webhook_check.scalar_one_or_none.return_value = None
    acquisto_result = MagicMock()
    acquisto_result.scalar_one_or_none.return_value = acquisto_mock
    links_result = MagicMock()
    links_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[webhook_check, acquisto_result, links_result])

    with patch("modules.webhooks.stripe_handler.stripe.Webhook.construct_event", return_value=real_event):
        result = await stripe_webhook(_fake_request(payload_dict), db=db)

    assert result == {"status": "ok"}
    assert acquisto_mock.stato == "fallito"


@pytest.mark.asyncio
async def test_webhook_charge_refunded_legge_payment_intent_reale():
    """charge.refunded legge payment_intent dal charge — stesso pattern .to_dict().get()."""
    from modules.webhooks.stripe_handler import stripe_webhook

    payload_dict = {
        "id": "evt_test_refund",
        "object": "event",
        "type": "charge.refunded",
        "data": {"object": {
            "id": "ch_test_regressione",
            "object": "charge",
            "payment_intent": "pi_test_regressione",
        }},
    }
    real_event = stripe.Event.construct_from(payload_dict, "sk_test_x")

    acquisto_mock = MagicMock()
    acquisto_mock.stato = "pagato"

    db = _mock_db()
    webhook_check = MagicMock()
    webhook_check.scalar_one_or_none.return_value = None
    acquisto_result = MagicMock()
    acquisto_result.scalar_one_or_none.return_value = acquisto_mock
    links_result = MagicMock()
    links_result.all.return_value = []
    db.execute = AsyncMock(side_effect=[webhook_check, acquisto_result, links_result])

    with patch("modules.webhooks.stripe_handler.stripe.Webhook.construct_event", return_value=real_event):
        result = await stripe_webhook(_fake_request(payload_dict), db=db)

    assert result == {"status": "ok"}
    assert acquisto_mock.stato == "rimborsato"
