"""Lógica de negocio del módulo IA — CU29 (recomendador), CU30 (chatbot),
CU32 (reporte por comando de voz). Usa Gemini vía `gemini_client`."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session, func, select

from app.modules.ia import gemini_client
from app.modules.inventario.models import Inventario
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.productos.service import _catalogo_producto_out
from app.modules.ventas.models import EstadoVenta, Venta, VentaDetalle

ESTADOS_PAGADOS = (EstadoVenta.PAGADA, EstadoVenta.COMPLETADA)


# --------------------------------------------------------------------------- #
#  CU29 — Recibir Recomendaciones de Productos
# --------------------------------------------------------------------------- #
def _categorias_compradas(session: Session, cliente_id: int) -> list[str]:
    filas = session.exec(
        select(Producto.categoria_id)
        .select_from(VentaDetalle)
        .join(Venta, Venta.id == VentaDetalle.venta_id)
        .join(ProductoVariante, ProductoVariante.id == VentaDetalle.variante_id)
        .join(Producto, Producto.id == ProductoVariante.producto_id)
        .where(Venta.cliente_id == cliente_id, Venta.estado.in_(ESTADOS_PAGADOS))
    ).all()
    if not filas:
        return []
    from app.modules.catalogo.models import Categoria

    ids = list({f for f in filas})
    categorias = session.exec(select(Categoria).where(Categoria.id.in_(ids))).all()
    return [c.nombre for c in categorias]


def _catalogo_para_ia(session: Session, limite: int = 60) -> list[Producto]:
    return session.exec(
        select(Producto)
        .where(Producto.activo == True, Producto.precio_base.is_not(None))  # noqa: E712
        .order_by(Producto.fecha_creacion.desc())
        .limit(limite)
    ).all()


def recomendar_productos(session: Session, cliente_id: int) -> list[dict]:
    categorias_previas = _categorias_compradas(session, cliente_id)
    candidatos = _catalogo_para_ia(session)

    if not candidatos:
        return []

    lista_candidatos = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "categoria_id": p.categoria_id,
            "precio_base": float(p.precio_base),
        }
        for p in candidatos
    ]

    prompt = (
        f"Historial de compras del cliente (categorías): "
        f"{', '.join(categorias_previas) if categorias_previas else 'sin compras previas'}.\n"
        f"Catálogo disponible (JSON): {lista_candidatos}\n"
        f"Elegí hasta 6 productos del catálogo que más le convendría ver a este "
        f"cliente, considerando su historial, variedad de categorías y precio. "
        f"Si no tiene historial, elegí una selección variada e interesante."
    )
    instruccion = (
        "Sos el motor de recomendaciones de FashionStore, una tienda de ropa. "
        "Respondé SIEMPRE con un array JSON válido, sin texto adicional, con "
        'objetos de la forma {"id": <int>, "motivo": "<razón breve en español, '
        'máx 12 palabras>"}. Los ids deben existir en el catálogo dado, nunca '
        "inventes ids."
    )

    ids_validos = {p.id for p in candidatos}
    try:
        resultado = gemini_client.generar_json(prompt, instruccion)
        elegidos = [
            it
            for it in resultado
            if isinstance(it, dict) and it.get("id") in ids_validos
        ][:6]
    except Exception:  # noqa: BLE001 — si la IA falla, no rompemos la pantalla
        elegidos = []

    if not elegidos:
        # Sin IA disponible (o sin resultado usable): igual mostramos algo,
        # con un motivo genérico en vez de dejar la sección vacía.
        elegidos = [
            {"id": p.id, "motivo": "Novedad de temporada"} for p in candidatos[:6]
        ]

    por_id = {p.id: p for p in candidatos}
    salida = []
    for it in elegidos:
        p = por_id.get(it["id"])
        if p is None:
            continue
        base = _catalogo_producto_out(session, p)
        salida.append(
            {
                "id": base["id"],
                "nombre": base["nombre"],
                "categoria": base["categoria"],
                "temporada": base["temporada"],
                "precio_base": base["precio_base"],
                "imagen_url": base["imagen_url"],
                "motivo": it.get("motivo", "Recomendado para vos"),
            }
        )
    return salida


# --------------------------------------------------------------------------- #
#  CU30 — Consultar Asistente Virtual (Chatbot)
# --------------------------------------------------------------------------- #
def chat_asistente(session: Session, mensaje: str, historial: list[dict]) -> dict:
    candidatos = _catalogo_para_ia(session, limite=40)
    lista_candidatos = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "precio_base": float(p.precio_base),
        }
        for p in candidatos
    ]

    historial_txt = "\n".join(
        f"{h['rol']}: {h['texto']}" for h in historial[-10:]
    )

    prompt = (
        f"Historial reciente de la conversación:\n{historial_txt or '(sin historial)'}\n\n"
        f"Catálogo disponible (JSON, para referenciar por id si corresponde): "
        f"{lista_candidatos}\n\n"
        f'Mensaje nuevo del cliente: "{mensaje}"'
    )
    instruccion = (
        "Sos el asistente virtual de FashionStore (tienda de ropa). Ayudás al "
        "cliente a encontrar prendas, respondés dudas sobre el catálogo, y sos "
        "breve, amable y en español. Respondé SIEMPRE con un JSON válido de la "
        'forma {"respuesta": "<texto para el cliente>", "producto_ids": [<ids '
        "del catálogo dado que mencionaste o recomendaste, puede ser vacío>]}. "
        "Nunca inventes productos ni ids fuera del catálogo dado."
    )

    try:
        resultado = gemini_client.generar_json(prompt, instruccion)
        respuesta = str(resultado.get("respuesta", "")).strip()
        ids_mencionados = resultado.get("producto_ids", []) or []
    except Exception:  # noqa: BLE001
        respuesta = (
            "No pude procesar tu consulta en este momento. Probá de nuevo en "
            "unos segundos, o mirá el catálogo directamente."
        )
        ids_mencionados = []

    if not respuesta:
        respuesta = "¿Podés reformular tu consulta? No estoy seguro de haber entendido."

    ids_validos = {p.id for p in candidatos}
    por_id = {p.id: p for p in candidatos}
    productos = [
        {
            "id": pid,
            "nombre": por_id[pid].nombre,
            "precio_base": por_id[pid].precio_base,
            "imagen_url": por_id[pid].imagen_url,
        }
        for pid in ids_mencionados
        if pid in ids_validos
    ][:6]

    return {"respuesta": respuesta, "productos": productos}


# --------------------------------------------------------------------------- #
#  CU32 — Generar Reporte por Comando de Voz
# --------------------------------------------------------------------------- #
def _metricas_para_reporte(session: Session) -> dict:
    ahora = datetime.now(timezone.utc)
    hace_7d = ahora - timedelta(days=7)
    hace_30d = ahora - timedelta(days=30)

    def _totales(desde: datetime) -> tuple[int, Decimal]:
        fila = session.exec(
            select(func.count(Venta.id), func.coalesce(func.sum(Venta.total), 0))
            .where(Venta.estado.in_(ESTADOS_PAGADOS), Venta.fecha_creacion >= desde)
        ).first()
        return fila[0] or 0, fila[1] or Decimal("0")

    cant_7d, total_7d = _totales(hace_7d)
    cant_30d, total_30d = _totales(hace_30d)

    top_productos = session.exec(
        select(
            Producto.nombre,
            func.sum(VentaDetalle.cantidad).label("unidades"),
        )
        .select_from(VentaDetalle)
        .join(Venta, Venta.id == VentaDetalle.venta_id)
        .join(ProductoVariante, ProductoVariante.id == VentaDetalle.variante_id)
        .join(Producto, Producto.id == ProductoVariante.producto_id)
        .where(Venta.estado.in_(ESTADOS_PAGADOS), Venta.fecha_creacion >= hace_30d)
        .group_by(Producto.nombre)
        .order_by(func.sum(VentaDetalle.cantidad).desc())
        .limit(5)
    ).all()

    UMBRAL_STOCK_BAJO = 3
    stock_bajo = session.exec(
        select(func.count(Inventario.id)).where(
            Inventario.cantidad_disponible <= UMBRAL_STOCK_BAJO
        )
    ).first()

    return {
        "ventas_ultimos_7_dias": {"cantidad": cant_7d, "total_bs": float(total_7d)},
        "ventas_ultimos_30_dias": {"cantidad": cant_30d, "total_bs": float(total_30d)},
        "productos_mas_vendidos_30_dias": [
            {"nombre": n, "unidades": int(u)} for n, u in top_productos
        ],
        "variantes_con_stock_bajo": stock_bajo or 0,
        "umbral_stock_bajo": UMBRAL_STOCK_BAJO,
    }


def generar_reporte_voz(session: Session, texto_comando: str) -> str:
    metricas = _metricas_para_reporte(session)

    prompt = (
        f"Pedido del administrador (transcripción de voz): \"{texto_comando}\"\n\n"
        f"Datos reales disponibles del sistema (JSON), son los únicos datos "
        f"que existen — no hay más información que esta: {metricas}"
    )
    instruccion = (
        "Sos el generador de reportes de FashionStore. Redactá un reporte breve "
        "en español, en 3-6 líneas, dirigido a un administrador, usando "
        "EXCLUSIVAMENTE los datos numéricos provistos (nunca inventes cifras "
        "que no estén en los datos). Si el pedido del administrador pide algo "
        "que no está en los datos disponibles, decilo explícitamente en vez de "
        "inventarlo. No respondas en JSON, solo el texto del reporte."
    )
    try:
        return gemini_client.generar_texto(prompt, instruccion)
    except Exception:  # noqa: BLE001
        return (
            "No se pudo generar el reporte con IA en este momento. Datos "
            f"disponibles: {metricas}"
        )
