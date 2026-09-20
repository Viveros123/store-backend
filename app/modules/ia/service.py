"""Lógica de negocio del módulo IA — CU29 (recomendador), CU30 (chatbot),
CU32 (reporte por comando de voz). Usa Gemini vía `gemini_client`."""

import operator as _operator
from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, func, select

from fastapi import HTTPException

from app.modules.catalogo.models import Color, Talla
from app.modules.ia import gemini_client
from app.modules.ia.models import (
    FormatoSolicitud,
    HistorialInteraccion,
    ReporteGenerado,
    TipoInteraccion,
    TipoReporte,
)
from app.modules.inventario.models import Inventario
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.productos.service import _catalogo_producto_out
from app.modules.promociones import service as promociones_service
from app.modules.sucursales.models import Sucursal
from app.modules.ventas import service as ventas_service
from app.modules.ventas.models import EstadoVenta, Venta, VentaDetalle
from app.modules.ventas.schemas import ItemCarritoCreate

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
                "precio_promocional": base["precio_promocional"],
                "imagen_url": base["imagen_url"],
                "motivo": it.get("motivo", "Recomendado para vos"),
            }
        )
    return salida


def _variantes_por_producto(
    session: Session, producto_ids: list[int]
) -> dict[int, list[dict]]:
    """Variantes reales (talla+color+id) de cada producto, con las sucursales
    donde hay stock — así el chatbot puede responder qué talla/color tiene
    cada prenda (en vez de inventarlo) y, si corresponde, agregar la
    variante exacta al carrito en vez de adivinar un id."""
    if not producto_ids:
        return {}
    filas = session.exec(
        select(
            ProductoVariante.producto_id,
            ProductoVariante.id,
            ProductoVariante.precio,
            Talla.valor,
            Color.nombre,
            Sucursal.nombre,
            Inventario.cantidad_disponible,
        )
        .join(Talla, Talla.id == ProductoVariante.talla_id)
        .join(Color, Color.id == ProductoVariante.color_id)
        .outerjoin(Inventario, Inventario.variante_id == ProductoVariante.id)
        .outerjoin(Sucursal, Sucursal.id == Inventario.sucursal_id)
        .where(ProductoVariante.producto_id.in_(producto_ids))
    ).all()

    agrupado: dict[int, dict[int, dict]] = {}
    for producto_id, variante_id, precio, talla, color, sucursal_nombre, cantidad in filas:
        variantes = agrupado.setdefault(producto_id, {})
        variante = variantes.setdefault(
            variante_id,
            {
                "id": variante_id,
                "talla": talla,
                "color": color,
                "precio_propio": precio,  # None = usa el precio del producto
                "sucursales_con_stock": [],
            },
        )
        if sucursal_nombre and cantidad and cantidad > 0:
            if sucursal_nombre not in variante["sucursales_con_stock"]:
                variante["sucursales_con_stock"].append(sucursal_nombre)

    return {pid: list(vs.values()) for pid, vs in agrupado.items()}


# --------------------------------------------------------------------------- #
#  CU30 — Consultar Asistente Virtual (Chatbot)
# --------------------------------------------------------------------------- #
def chat_asistente(
    session: Session, cliente_id: int, mensaje: str, historial: list[dict]
) -> dict:
    candidatos = _catalogo_para_ia(session, limite=40)
    variantes_por_producto = _variantes_por_producto(
        session, [p.id for p in candidatos]
    )
    promos_por_producto = promociones_service.promos_vigentes_por_producto(
        session, [p.id for p in candidatos]
    )
    precios_promo: dict[int, tuple] = {}
    for p in candidatos:
        final, promo = promociones_service.mejor_precio(
            p.precio_base, promos_por_producto.get(p.id, [])
        )
        if promo:
            precios_promo[p.id] = (final, promo)

    # Precio y promoción de cada variante (la promoción puede cubrir el
    # producto completo o solo algunas variantes).
    promos_por_variante = promociones_service.promos_vigentes_por_variante(
        session,
        [(v["id"], p.id) for p in candidatos for v in variantes_por_producto.get(p.id, [])],
    )
    variantes_ia: dict[int, list[dict]] = {}
    for p in candidatos:
        lista = []
        for v in variantes_por_producto.get(p.id, []):
            efectivo = v["precio_propio"] if v["precio_propio"] is not None else p.precio_base
            final, promo = promociones_service.mejor_precio(
                efectivo, promos_por_variante.get(v["id"], [])
            )
            entrada = {k: val for k, val in v.items() if k != "precio_propio"}
            entrada["precio"] = float(efectivo)
            entrada["promocion"] = (
                {"nombre": promo.nombre, "precio_con_descuento": float(final)}
                if promo
                else None
            )
            lista.append(entrada)
        variantes_ia[p.id] = lista

    lista_candidatos = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "precio_base": float(p.precio_base),
            "variantes": variantes_ia[p.id],
        }
        for p in candidatos
    ]

    historial_txt = "\n".join(
        f"{h['rol']}: {h['texto']}" for h in historial[-10:]
    )

    prompt = (
        f"Historial reciente de la conversación:\n{historial_txt or '(sin historial)'}\n\n"
        f"Catálogo disponible (JSON — cada producto trae sus variantes reales "
        f"con id, talla, color y en qué sucursales hay stock ahora mismo): "
        f"{lista_candidatos}\n\n"
        f'Mensaje nuevo del cliente: "{mensaje}"'
    )
    instruccion = (
        "Sos el asistente virtual de FashionStore (tienda de ropa). Ayudás al "
        "cliente a encontrar prendas, respondés dudas sobre el catálogo "
        "(incluida disponibilidad por sucursal), y sos breve, amable y en "
        "español. Nunca inventes productos, ids, tallas, colores, precios, "
        "sucursales ni ningún otro dato que no esté en el catálogo dado: si "
        "te preguntan algo que no figura ahí (ej. stock exacto en unidades, "
        "reservas), decilo explícitamente en vez de adivinar. Cada variante trae su "
        "\"precio\" y, si tiene \"promocion\", ese es el precio que realmente se "
        "cobra por esa variante: mencioná el precio con descuento y el nombre de "
        "la promoción (si solo algunas variantes de un producto tienen "
        "promoción, aclará cuáles). Los "
        "precios están en bolivianos: escribilos como \"Bs 75.00\", nunca "
        "con el signo $.\n\n"
        "Además podés AGREGAR PRENDAS AL CARRITO del cliente de verdad "
        "(no es solo hablar). Hacelo solo cuando: (1) el cliente pidió "
        "agregar/comprar algo y vos identificaste una única variante exacta "
        "(id concreto) que tiene al menos una sucursal con stock, y (2) ya "
        "tenés confirmación clara del cliente sobre qué talla y color quiere "
        "(si hay más de una combinación posible y no lo especificó, primero "
        "PREGUNTÁ cuál quiere en vez de elegir por él). Cuando corresponda "
        "agregar, incluí el campo \"accion\". Si falta información o no "
        "corresponde agregar nada, \"accion\" debe ser null.\n\n"
        'Respondé SIEMPRE con un JSON válido de la forma {"respuesta": '
        '"<texto para el cliente>", "producto_ids": [<ids del catálogo que '
        'mencionaste, puede ser vacío>], "accion": null o {"tipo": '
        '"agregar_carrito", "variante_id": <id de variante del catálogo '
        'dado>, "cantidad": <entero, 1 si no se especificó>}}.'
    )

    accion = None
    try:
        resultado = gemini_client.generar_json(prompt, instruccion)
        respuesta = str(resultado.get("respuesta", "")).strip()
        ids_mencionados = resultado.get("producto_ids", []) or []
        accion = resultado.get("accion")
    except Exception:  # noqa: BLE001
        respuesta = (
            "No pude procesar tu consulta en este momento. Probá de nuevo en "
            "unos segundos, o mirá el catálogo directamente."
        )
        ids_mencionados = []

    if not respuesta:
        respuesta = "¿Podés reformular tu consulta? No estoy seguro de haber entendido."

    carrito_actualizado = False
    if isinstance(accion, dict) and accion.get("tipo") == "agregar_carrito":
        variantes_validas = {
            v["id"] for vs in variantes_por_producto.values() for v in vs
        }
        variante_id = accion.get("variante_id")
        cantidad = accion.get("cantidad") or 1
        if variante_id in variantes_validas:
            try:
                cantidad = max(1, min(int(cantidad), 20))
                ventas_service.agregar_item(
                    session,
                    cliente_id,
                    ItemCarritoCreate(variante_id=variante_id, cantidad=cantidad),
                )
                carrito_actualizado = True
                respuesta += " ✅ Lo agregué a tu carrito."
            except HTTPException as e:
                respuesta += f" (No pude agregarlo: {e.detail})"

    ids_validos = {p.id for p in candidatos}
    por_id = {p.id: p for p in candidatos}
    productos = [
        {
            "id": pid,
            "nombre": por_id[pid].nombre,
            "precio_base": por_id[pid].precio_base,
            "precio_promocional": precios_promo[pid][0] if pid in precios_promo else None,
            "imagen_url": por_id[pid].imagen_url,
        }
        for pid in ids_mencionados
        if pid in ids_validos
    ][:6]

    session.add(
        HistorialInteraccion(
            cliente_id=cliente_id,
            tipo=TipoInteraccion.CHATBOT,
            producto_id=productos[0]["id"] if productos else None,
            consulta=mensaje,
            respuesta=respuesta,
        )
    )
    session.commit()

    return {
        "respuesta": respuesta,
        "productos": productos,
        "carrito_actualizado": carrito_actualizado,
    }


# --------------------------------------------------------------------------- #
#  CU32 — Generar Reporte por Comando de Voz
# --------------------------------------------------------------------------- #
_COMPARADORES_STOCK = {
    "menor_igual": _operator.le,
    "mayor_igual": _operator.ge,
    "igual": _operator.eq,
    "menor": _operator.lt,
    "mayor": _operator.gt,
}
_TOPE_VENTAS_DETALLE = 30


def _sucursales_activas(session: Session) -> list[Sucursal]:
    return session.exec(select(Sucursal).where(Sucursal.activa == True)).all()  # noqa: E712


def _parsear_fecha(valor) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def _extraer_intencion_reporte(texto_comando: str, sucursales: list[Sucursal]) -> dict:
    """Paso 1: le pedimos a Gemini que traduzca el pedido de voz (libre, en
    español) a filtros estructurados. No se ejecuta nada todavía — recién en
    el paso 2 se valida esto contra datos reales y se corren las consultas."""
    hoy = datetime.now(timezone.utc).date()
    prompt = (
        f"Hoy es {hoy.isoformat()}.\n"
        f"Sucursales reales activas: {[s.nombre for s in sucursales]}\n"
        f'Pedido del administrador (transcripción de voz): "{texto_comando}"'
    )
    instruccion = (
        "Interpretá qué reporte de ventas/stock pide un administrador de una "
        "tienda de ropa, y devolvé SOLO un JSON con esta forma exacta: "
        '{"fecha_desde": "YYYY-MM-DD" o null, "fecha_hasta": "YYYY-MM-DD" o '
        'null, "sucursal": "<nombre EXACTO de la lista de sucursales reales>" '
        'o null, "comparar_sucursales": true/false, "incluir_detalle_ventas": '
        'true/false, "stock_comparador": "menor_igual"|"mayor_igual"|"igual"|'
        '"menor"|"mayor" o null, "stock_umbral": <entero> o null}.\n\n'
        "Reglas: calculá fechas relativas (ej. 'últimas 2 semanas' = hace 14 "
        "días hasta hoy, 'ayer', 'este mes') tomando como referencia la fecha "
        "de hoy dada arriba. Si no mencionó ningún período dejá ambas fechas "
        "en null. \"sucursal\" debe ser exactamente uno de los nombres reales "
        "dados o null — nunca inventes un nombre que no esté en la lista. "
        "\"comparar_sucursales\" es true si pidió comparar ventas entre "
        "sucursales. \"incluir_detalle_ventas\" es true si pidió ver ventas "
        "puntuales/exactas, no solo totales. \"stock_comparador\"/"
        "\"stock_umbral\" solo si pidió stock comparado con un número exacto; "
        "si no, dejalos null."
    )
    try:
        resultado = gemini_client.generar_json(prompt, instruccion)
        return resultado if isinstance(resultado, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _validar_intencion_reporte(intencion: dict, sucursales: list[Sucursal]) -> dict:
    """Paso 2 (validación): nunca confiamos ciegamente en lo que devolvió la
    IA — fechas inválidas caen a un rango por defecto, y una sucursal que no
    coincide con ninguna real se descarta (y se avisa en vez de inventar)."""
    hoy = datetime.now(timezone.utc).date()
    desde = _parsear_fecha(intencion.get("fecha_desde")) or (hoy - timedelta(days=30))
    hasta = _parsear_fecha(intencion.get("fecha_hasta")) or hoy
    if desde > hasta:
        desde, hasta = hasta, desde

    por_nombre = {s.nombre.lower(): s for s in sucursales}
    nombre_pedido = intencion.get("sucursal")
    sucursal = por_nombre.get(str(nombre_pedido).lower()) if nombre_pedido else None

    comparador = intencion.get("stock_comparador")
    if comparador not in _COMPARADORES_STOCK:
        comparador = None
    try:
        umbral = intencion.get("stock_umbral")
        umbral = int(umbral) if umbral is not None else None
    except (TypeError, ValueError):
        umbral = None

    return {
        "fecha_desde": desde,
        "fecha_hasta": hasta,
        "sucursal": sucursal,
        "sucursal_no_reconocida": nombre_pedido if nombre_pedido and sucursal is None else None,
        "comparar_sucursales": bool(intencion.get("comparar_sucursales")),
        "incluir_detalle_ventas": bool(intencion.get("incluir_detalle_ventas")),
        "stock_comparador": comparador,
        "stock_umbral": umbral,
    }


def _condiciones_ventas(desde: date, hasta: date, sucursal_id: int | None) -> list:
    desde_dt = datetime.combine(desde, datetime.min.time(), tzinfo=timezone.utc)
    hasta_dt = datetime.combine(hasta, datetime.max.time(), tzinfo=timezone.utc)
    cond = [
        Venta.estado.in_(ESTADOS_PAGADOS),
        Venta.fecha_creacion >= desde_dt,
        Venta.fecha_creacion <= hasta_dt,
    ]
    if sucursal_id is not None:
        cond.append(Venta.sucursal_id == sucursal_id)
    return cond


def _ventas_totales_rango(
    session: Session, desde: date, hasta: date, sucursal_id: int | None
) -> tuple[int, float]:
    fila = session.exec(
        select(func.count(Venta.id), func.coalesce(func.sum(Venta.total), 0)).where(
            *_condiciones_ventas(desde, hasta, sucursal_id)
        )
    ).first()
    return fila[0] or 0, float(fila[1] or 0)


def _ventas_por_sucursal(session: Session, desde: date, hasta: date) -> list[dict]:
    filas = session.exec(
        select(
            Sucursal.nombre,
            func.count(Venta.id),
            func.coalesce(func.sum(Venta.total), 0),
        )
        .select_from(Venta)
        .join(Sucursal, Sucursal.id == Venta.sucursal_id)
        .where(*_condiciones_ventas(desde, hasta, None))
        .group_by(Sucursal.nombre)
        .order_by(func.coalesce(func.sum(Venta.total), 0).desc())
    ).all()
    return [
        {"sucursal": nombre, "cantidad_ventas": cant, "total_bs": float(total)}
        for nombre, cant, total in filas
    ]


def _top_productos_rango(
    session: Session, desde: date, hasta: date, sucursal_id: int | None, limite: int = 5
) -> list[dict]:
    filas = session.exec(
        select(Producto.nombre, func.sum(VentaDetalle.cantidad))
        .select_from(VentaDetalle)
        .join(Venta, Venta.id == VentaDetalle.venta_id)
        .join(ProductoVariante, ProductoVariante.id == VentaDetalle.variante_id)
        .join(Producto, Producto.id == ProductoVariante.producto_id)
        .where(*_condiciones_ventas(desde, hasta, sucursal_id))
        .group_by(Producto.nombre)
        .order_by(func.sum(VentaDetalle.cantidad).desc())
        .limit(limite)
    ).all()
    return [{"nombre": n, "unidades": int(u)} for n, u in filas]


def _detalle_ventas_rango(
    session: Session, desde: date, hasta: date, sucursal_id: int | None
) -> list[dict]:
    filas = session.exec(
        select(Venta.id, Venta.fecha_creacion, Venta.total, Sucursal.nombre)
        .select_from(Venta)
        .join(Sucursal, Sucursal.id == Venta.sucursal_id)
        .where(*_condiciones_ventas(desde, hasta, sucursal_id))
        .order_by(Venta.fecha_creacion.desc())
        .limit(_TOPE_VENTAS_DETALLE)
    ).all()
    return [
        {
            "venta_id": vid,
            "fecha": fecha.date().isoformat(),
            "total_bs": float(total),
            "sucursal": sucursal_nombre,
        }
        for vid, fecha, total, sucursal_nombre in filas
    ]


def _stock_consultado(session: Session, comparador: str | None, umbral: int | None) -> dict:
    comparador = comparador or "menor_igual"
    umbral = 3 if umbral is None else umbral
    op = _COMPARADORES_STOCK[comparador]
    filas = session.exec(
        select(
            Producto.nombre,
            Talla.valor,
            Color.nombre,
            Sucursal.nombre,
            Inventario.cantidad_disponible,
        )
        .select_from(Inventario)
        .join(ProductoVariante, ProductoVariante.id == Inventario.variante_id)
        .join(Producto, Producto.id == ProductoVariante.producto_id)
        .join(Talla, Talla.id == ProductoVariante.talla_id)
        .join(Color, Color.id == ProductoVariante.color_id)
        .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
        .where(op(Inventario.cantidad_disponible, umbral), Sucursal.activa == True)  # noqa: E712
        .order_by(Inventario.cantidad_disponible.asc())
        .limit(30)
    ).all()
    return {
        "comparador": comparador,
        "umbral": umbral,
        "items": [
            {
                "producto": nombre,
                "talla": talla,
                "color": color,
                "sucursal": sucursal_nombre,
                "stock": cantidad,
            }
            for nombre, talla, color, sucursal_nombre, cantidad in filas
        ],
    }


def generar_reporte_voz(session: Session, usuario_id: int, texto_comando: str) -> str:
    sucursales = _sucursales_activas(session)

    intencion_ia = _extraer_intencion_reporte(texto_comando, sucursales)
    filtros = _validar_intencion_reporte(intencion_ia, sucursales)

    desde, hasta = filtros["fecha_desde"], filtros["fecha_hasta"]
    sucursal = filtros["sucursal"]
    sucursal_id = sucursal.id if sucursal else None

    cantidad, total_bs = _ventas_totales_rango(session, desde, hasta, sucursal_id)
    metricas: dict = {
        "periodo_interpretado": f"{desde.isoformat()} a {hasta.isoformat()}",
        "sucursal_filtrada": sucursal.nombre if sucursal else "todas",
        "ventas_en_periodo": {"cantidad": cantidad, "total_bs": total_bs},
        "productos_mas_vendidos_en_periodo": _top_productos_rango(
            session, desde, hasta, sucursal_id
        ),
    }
    if filtros["sucursal_no_reconocida"]:
        metricas["aviso"] = (
            f'El administrador mencionó una sucursal ("{filtros["sucursal_no_reconocida"]}") '
            "que no coincide con ninguna sucursal real activa; se muestran datos de todas."
        )
    if filtros["comparar_sucursales"]:
        metricas["ventas_por_sucursal_en_periodo"] = _ventas_por_sucursal(session, desde, hasta)
    if filtros["incluir_detalle_ventas"]:
        detalle = _detalle_ventas_rango(session, desde, hasta, sucursal_id)
        metricas["ventas_detalle"] = detalle
        metricas["ventas_detalle_truncado"] = cantidad > len(detalle)
    metricas["stock_consultado"] = _stock_consultado(
        session, filtros["stock_comparador"], filtros["stock_umbral"]
    )

    prompt = (
        f'Pedido del administrador (transcripción de voz): "{texto_comando}"\n\n'
        f"Datos reales disponibles del sistema (JSON), son los únicos datos "
        f"que existen — no hay más información que esta: {metricas}"
    )
    instruccion = (
        "Sos el generador de reportes de FashionStore. Redactá un reporte breve "
        "en español, dirigido a un administrador, usando EXCLUSIVAMENTE los "
        "datos provistos (nunca inventes cifras, sucursales ni productos que no "
        "estén ahí). SIEMPRE mencioná al inicio qué período de fechas y qué "
        "sucursal se usó para armar el reporte (periodo_interpretado / "
        "sucursal_filtrada), así el administrador puede confirmar que se "
        "entendió bien su pedido. Si hay un campo 'aviso', comunicalo. Si "
        "ventas_detalle_truncado es true, aclará que se muestran solo las "
        "últimas 30 ventas del período y que hay más. Si el pedido pide algo "
        "que no está en los datos, decilo explícitamente en vez de inventarlo. "
        "No respondas en JSON, solo el texto del reporte."
    )
    try:
        reporte = gemini_client.generar_texto(prompt, instruccion)
    except Exception:  # noqa: BLE001
        reporte = (
            "No se pudo generar el reporte con IA en este momento. Datos "
            f"disponibles: {metricas}"
        )

    session.add(
        ReporteGenerado(
            usuario_id=usuario_id,
            tipo_reporte=TipoReporte.GENERAL,
            formato_solicitud=FormatoSolicitud.VOZ,
            parametros={
                "comando": texto_comando,
                "fecha_desde": desde.isoformat(),
                "fecha_hasta": hasta.isoformat(),
                "sucursal": sucursal.nombre if sucursal else None,
                "comparar_sucursales": filtros["comparar_sucursales"],
                "incluir_detalle_ventas": filtros["incluir_detalle_ventas"],
                "stock_comparador": filtros["stock_comparador"],
                "stock_umbral": filtros["stock_umbral"],
            },
        )
    )
    session.commit()
    return reporte
