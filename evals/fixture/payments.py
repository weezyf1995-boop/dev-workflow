"""Charge a customer's card for an invoice."""

MAX_RETRIES = 3


def charge(invoice_id, amount_cents, gateway):
    """Try the gateway up to MAX_RETRIES times; return the charge id or None."""
    for _ in range(MAX_RETRIES):
        charge_id = gateway.charge(invoice_id, amount_cents)
        if charge_id is not None:
            return charge_id
    return None
