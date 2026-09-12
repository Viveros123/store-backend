"""Lógica de negocio del módulo Reservas — CU16."""

from datetime import date, datetime, time

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.modules.catalogo.models import Color, Talla
from app.modules.inventario.models import Inventario, MovimientoInventario, TipoMovimiento
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.reservas.models import EstadoReserva, Reserva, ReservaDetalle
from app.modules.reservas.schemas import ReservaCreate, SlotsDisponibilidad
from app.modules.sucursales.models import Sucursal
from app.modules.sucursales.service import horario_del_dia

DURACIONES_VALIDAS = (30, 60)


def _a_minutos(t: time) -> int:
    return t.hour * 60 + t.minute


def _a_hora(minutos: int) -> time:
    return time(hour=minutos // 60, minute=minutos % 60)


def _get_sucursal_activa(session: Session, sucursal_id: int) -> Sucursal:
    sucursal = session.get(Sucursal, sucursal_id)
    if sucursal is None or not sucursal.activa:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sucursal no encontrada")
    return sucursal


def _reservas_activas_del_dia(
    session: Session, sucursal_id: int, fecha: date
) -> list[Reserva]:
    return session.exec(
        select(Reserva).where(
            Reserva.sucursal_id == sucursal_id,
            Reserva.fecha == fecha,
            Reserva.estado.in_(EstadoReserva.ACTIVOS),
        )
    ).all()


# --------------------------------------------------------------------------- #
#  Consultar turnos libres
# --------------------------------------------------------------------------- #
def slots_disponibles(
    session: Session, sucursal_id: int, fecha: date, duracion_minutos: int
) -> SlotsDisponibilidad:
    if duracion_minutos not in DURACIONES_VALIDAS:
        raise HTTPException(422, "La duración del turno debe ser 30 o 60 minutos")
    _get_sucursal_activa(session, sucursal_id)
    if fecha < date.today():
        return SlotsDisponibilidad(
            fecha=fecha, duracion_minutos=duracion_minutos, cerrado=True, slots=[]
        )

    horario = horario_del_dia(session, sucursal_id, fecha.weekday())
    if horario.cerrado or horario.hora_apertura is None or horario.hora_cierre is None:
        return SlotsDisponibilidad(
            fecha=fecha, duracion_minutos=duracion_minutos, cerrado=True, slots=[]
        )

    apertura = _a_minutos(horario.hora_apertura)
    cierre = _a_minutos(horario.hora_cierre)

    ocupados = [
        (_a_minutos(r.hora_inicio), _a_minutos(r.hora_fin))
        for r in _reservas_activas_del_dia(session, sucursal_id, fecha)
    ]

    limite_inferior = None
    if fecha == date.today():
        limite_inferior = _a_minutos(datetime.now().time())

    libres: list[time] = []
    cursor = apertura
    while cursor + duracion_minutos <= cierre:
        fin = cursor + duracion_minutos
        pasado = limite_inferior is not None and cursor <= limite_inferior
        solapa = any(cursor < o_fin and fin > o_inicio for o_inicio, o_fin in ocupados)
        if not pasado and not solapa:
            libres.append(_a_hora(cursor))
        cursor += 30

    return SlotsDisponibilidad(
        fecha=fecha, duracion_minutos=duracion_minutos, cerrado=False, slots=libres
    )


# --------------------------------------------------------------------------- #
#  Serialización
# --------------------------------------------------------------------------- #
def _reserva_out(session: Session, r: Reserva) -> dict:
    sucursal = session.get(Sucursal, r.sucursal_id)
    detalles = session.exec(
        select(ReservaDetalle).where(ReservaDetalle.reserva_id == r.id)
    ).all()
    items = []
    for d in detalles:
        variante = session.get(ProductoVariante, d.variante_id)
        producto = session.get(Producto, variante.producto_id) if variante else None
        talla = session.get(Talla, variante.talla_id) if variante else None
        color = session.get(Color, variante.color_id) if variante else None
        items.append(
            {
                "variante_id": d.variante_id,
                "producto_id": producto.id if producto else None,
                "producto": producto.nombre if producto else None,
                "talla": talla.valor if talla else None,
                "color": color.nombre if color else None,
                "sku": variante.sku if variante else None,
                "cantidad": d.cantidad,
            }
        )
    return {
        "id": r.id,
        "sucursal_id": r.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "ciudad": sucursal.ciudad if sucursal else None,
        "fecha": r.fecha,
        "hora_inicio": r.hora_inicio,
        "hora_fin": r.hora_fin,
        "duracion_minutos": r.duracion_minutos,
        "estado": r.estado,
        "fecha_creacion": r.fecha_creacion,
        "items": items,
    }


# --------------------------------------------------------------------------- #
#  Crear reserva
# --------------------------------------------------------------------------- #
def crear_reserva(session: Session, cliente_id: int, data: ReservaCreate) -> dict:
    if data.duracion_minutos not in DURACIONES_VALIDAS:
        raise HTTPException(422, "La duración del turno debe ser 30 o 60 minutos")
    if data.hora_inicio.minute not in (0, 30) or data.hora_inicio.second != 0:
        raise HTTPException(422, "El turno debe empezar en punto o y media")
    if data.fecha < date.today():
        raise HTTPException(422, "No se puede reservar en una fecha pasada")

    _get_sucursal_activa(session, data.sucursal_id)

    horario = horario_del_dia(session, data.sucursal_id, data.fecha.weekday())
    if horario.cerrado or horario.hora_apertura is None or horario.hora_cierre is None:
        raise HTTPException(409, "La sucursal está cerrada ese día")

    inicio_min = _a_minutos(data.hora_inicio)
    fin_min = inicio_min + data.duracion_minutos
    if inicio_min < _a_minutos(horario.hora_apertura) or fin_min > _a_minutos(
        horario.hora_cierre
    ):
        raise HTTPException(409, "Ese horario está fuera de la atención de la sucursal")

    if data.fecha == date.today() and inicio_min <= _a_minutos(datetime.now().time()):
        raise HTTPException(409, "Ese horario ya pasó")

    for r in _reservas_activas_del_dia(session, data.sucursal_id, data.fecha):
        if inicio_min < _a_minutos(r.hora_fin) and fin_min > _a_minutos(r.hora_inicio):
            raise HTTPException(409, "Ese turno ya está reservado por otro cliente")

    # Validar variantes + stock disponible en esa sucursal
    inventarios: dict[int, Inventario] = {}
    for item in data.items:
        if session.get(ProductoVariante, item.variante_id) is None:
            raise HTTPException(422, "Una de las prendas elegidas ya no existe")
        inv = session.exec(
            select(Inventario).where(
                Inventario.variante_id == item.variante_id,
                Inventario.sucursal_id == data.sucursal_id,
            )
        ).first()
        if inv is None or inv.cantidad_disponible < item.cantidad:
            raise HTTPException(
                422, "No hay stock suficiente de esa prenda en la sucursal elegida"
            )
        inventarios[item.variante_id] = inv

    reserva = Reserva(
        cliente_id=cliente_id,
        sucursal_id=data.sucursal_id,
        fecha=data.fecha,
        hora_inicio=data.hora_inicio,
        hora_fin=_a_hora(fin_min),
        duracion_minutos=data.duracion_minutos,
    )
    session.add(reserva)
    session.flush()  # necesitamos reserva.id para el detalle

    for item in data.items:
        inv = inventarios[item.variante_id]
        inv.cantidad_disponible -= item.cantidad
        inv.cantidad_reservada += item.cantidad
        session.add(inv)
        session.add(
            ReservaDetalle(
                reserva_id=reserva.id,
                variante_id=item.variante_id,
                cantidad=item.cantidad,
            )
        )

    session.commit()
    session.refresh(reserva)
    return _reserva_out(session, reserva)


def mis_reservas(session: Session, cliente_id: int) -> list[dict]:
    filas = session.exec(
        select(Reserva)
        .where(Reserva.cliente_id == cliente_id)
        .order_by(Reserva.fecha.desc(), Reserva.hora_inicio.desc())
    ).all()
    return [_reserva_out(session, r) for r in filas]


# --------------------------------------------------------------------------- #
#  CU17 — Cancelar reserva
# --------------------------------------------------------------------------- #
def cancelar_reserva(session: Session, cliente_id: int, reserva_id: int) -> dict:
    reserva = session.get(Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reserva no encontrada")
    if reserva.cliente_id != cliente_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Esta reserva es de otro cliente")
    if reserva.estado != EstadoReserva.PENDIENTE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta reserva ya no se puede cancelar (no está pendiente).",
        )

    detalles = session.exec(
        select(ReservaDetalle).where(ReservaDetalle.reserva_id == reserva_id)
    ).all()
    for d in detalles:
        inv = session.exec(
            select(Inventario).where(
                Inventario.variante_id == d.variante_id,
                Inventario.sucursal_id == reserva.sucursal_id,
            )
        ).first()
        if inv is not None:
            inv.cantidad_disponible += d.cantidad
            inv.cantidad_reservada = max(0, inv.cantidad_reservada - d.cantidad)
            session.add(inv)
        session.add(
            MovimientoInventario(
                variante_id=d.variante_id,
                sucursal_id=reserva.sucursal_id,
                usuario_id=cliente_id,
                tipo=TipoMovimiento.LIBERACION_RESERVA,
                cantidad=d.cantidad,
                nota=f"Cancelación de la reserva #{reserva.id}",
            )
        )

    reserva.estado = EstadoReserva.CANCELADA
    session.add(reserva)
    session.commit()
    session.refresh(reserva)
    return _reserva_out(session, reserva)
