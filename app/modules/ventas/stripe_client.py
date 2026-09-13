"""Integración con Stripe (modo test) — CU27/CU28.

Nota sobre moneda: Stripe no admite el Boliviano (BOB) como moneda de
cobro. Como estamos siempre en modo test (no se mueve plata real), se
cobra el equivalente en USD usando un tipo de cambio fijo aproximado
(el oficial, ~6.96 Bs/USD), solo para que el monto que ve Stripe tenga
sentido. Nada de esto afecta los montos en Bs que se guardan en la BD.
"""

import base64
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

import qrcode
import stripe

from app.core.config import settings

stripe.api_key = settings.stripe_secret_key

TIPO_CAMBIO_BOB_USD = Decimal("6.96")


def bs_a_usd(monto_bs: Decimal) -> Decimal:
    return (monto_bs / TIPO_CAMBIO_BOB_USD).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def crear_checkout_session(
    *,
    venta_id: int,
    monto_bs: Decimal,
    descripcion: str,
    success_url: str,
    cancel_url: str,
):
    monto_usd = bs_a_usd(monto_bs)
    return stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(monto_usd * 100),  # centavos
                    "product_data": {
                        "name": descripcion,
                        "description": f"Equivalente a Bs {monto_bs:.2f} (tipo de cambio de referencia)",
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"venta_id": str(venta_id)},
    )


def obtener_session(session_id: str):
    return stripe.checkout.Session.retrieve(session_id)


def generar_qr_data_url(contenido: str) -> str:
    """PNG en base64 (data URI) para <img [src]>, sin depender de nada del lado del cliente."""
    img = qrcode.make(contenido)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
