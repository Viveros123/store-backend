from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.catalogo.models import Categoria, Color, Talla
from app.modules.identidad.models import Usuario
from app.modules.inventario.models import Inventario
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.saas.models import CodigoFuncionalidad
from app.modules.saas.service import validar_acceso_plan
from app.modules.sucursales.models import Sucursal

from .schemas import DatosOfflineOut, ProductoOfflineOut, VarianteOfflineOut


def _sucursal_autorizada(
    session: Session, usuario: Usuario, sucursal_id: int | None
) -> Sucursal:
    if usuario.empresa_id is None:
        raise HTTPException(403, "El usuario no está asociado a una empresa")
    if usuario.sucursal_id is not None:
        if sucursal_id is not None and sucursal_id != usuario.sucursal_id:
            raise HTTPException(403, "No puede preparar datos de otra sucursal")
        sucursal_id = usuario.sucursal_id
    if sucursal_id is None:
        sucursales = session.exec(
            select(Sucursal).where(
                Sucursal.empresa_id == usuario.empresa_id,
                Sucursal.activa == True,  # noqa: E712
            )
        ).all()
        if len(sucursales) != 1:
            raise HTTPException(422, "Seleccione la sucursal que desea preparar")
        return sucursales[0]
    sucursal = session.get(Sucursal, sucursal_id)
    if (
        sucursal is None
        or sucursal.empresa_id != usuario.empresa_id
        or not sucursal.activa
    ):
        raise HTTPException(404, "Sucursal no encontrada para esta empresa")
    return sucursal


def preparar_datos(
    session: Session, usuario: Usuario, sucursal_id: int | None
) -> DatosOfflineOut:
    if usuario.empresa_id is None:
        raise HTTPException(403, "El usuario no está asociado a una empresa")
    validar_acceso_plan(
        session,
        usuario.empresa_id,
        funcionalidad=CodigoFuncionalidad.PWA_OFFLINE,
    )
    sucursal = _sucursal_autorizada(session, usuario, sucursal_id)
    filas = session.exec(
        select(Inventario, ProductoVariante, Producto, Categoria, Talla, Color)
        .join(ProductoVariante, ProductoVariante.id == Inventario.variante_id)
        .join(Producto, Producto.id == ProductoVariante.producto_id)
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .join(Talla, Talla.id == ProductoVariante.talla_id)
        .join(Color, Color.id == ProductoVariante.color_id)
        .where(
            Inventario.sucursal_id == sucursal.id,
            Producto.activo == True,  # noqa: E712
        )
        .order_by(Producto.nombre, ProductoVariante.id)
    ).all()

    productos: dict[int, ProductoOfflineOut] = {}
    for inventario, variante, producto, categoria, talla, color in filas:
        if producto.id not in productos:
            productos[producto.id] = ProductoOfflineOut(
                id=producto.id,
                nombre=producto.nombre,
                descripcion=producto.descripcion,
                categoria_id=categoria.id,
                categoria=categoria.nombre,
                precio_base=producto.precio_base,
                imagen_url=producto.imagen_url,
                variantes=[],
            )
        productos[producto.id].variantes.append(
            VarianteOfflineOut(
                id=variante.id,
                sku=variante.sku,
                talla_id=talla.id,
                talla=talla.valor,
                color_id=color.id,
                color=color.nombre,
                codigo_hex=color.codigo_hex,
                precio=variante.precio or producto.precio_base,
                imagen_url=variante.imagen_url or producto.imagen_url,
                cantidad_disponible=inventario.cantidad_disponible,
                cantidad_reservada=inventario.cantidad_reservada,
            )
        )

    ahora = datetime.now(timezone.utc)
    lista = list(productos.values())
    total_variantes = sum(len(item.variantes) for item in lista)
    return DatosOfflineOut(
        version_datos=f"1-{usuario.empresa_id}-{sucursal.id}-{int(ahora.timestamp())}",
        empresa_id=usuario.empresa_id,
        sucursal_id=sucursal.id,
        sucursal_nombre=sucursal.nombre,
        generado_en=ahora,
        productos=lista,
        total_productos=len(lista),
        total_variantes=total_variantes,
    )
