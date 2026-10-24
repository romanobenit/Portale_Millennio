from pathlib import Path

MODULES = Path(__file__).resolve().parents[2] / "modules"


def test_checkout_senza_payment_method_types():
    """Stripe rifiuta payment_method_types nelle Checkout Session: i metodi si gestiscono dalla dashboard."""
    colpevoli = [
        str(p.relative_to(MODULES))
        for p in MODULES.rglob("*.py")
        if "payment_method_types" in p.read_text(encoding="utf-8")
    ]
    assert colpevoli == []
