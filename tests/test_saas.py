"""Pruebas SaaS CU01-CU07 y preparación offline CU09."""

import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, func, select

from app.main import app
from app.modules.catalogo import service as catalogo_service
from app.modules.catalogo.models import Categoria, Color, Talla
from app.modules.identidad import service as identidad_service
from app.modules.identidad.models import Rol, RolNombre, Usuario
from app.modules.identidad.schemas import UsuarioCreate
from app.modules.ia import service as ia_service
from app.modules.inventario import service as inventario_service
from app.modules.inventario.models import Inventario
from app.modules.offline import service as offline_service
from app.modules.productos import service as productos_service
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.promociones.models import (
    Promocion,
    PromocionProducto,
    PromocionVariante,
)
from app.modules.promociones import service as promociones_service
from app.modules.proveedores import service as proveedores_service
from app.modules.proveedores.models import Proveedor
from app.modules.saas import service as saas_service
from app.modules.saas.models import (
    Empresa,
    FuncionalidadPlan,
    HistorialCambioPlan,
    LimitePlan,
    Plan,
    Suscripcion,
)
from app.modules.saas.schemas import (
    AdminInicialIn,
    CambioPlanIn,
    EmpresaCreate,
    EmpresaUpdate,
    FuncionalidadPlanIn,
    LimitePlanIn,
    PlanUpdate,
    SuscripcionGestionIn,
)
from app.modules.sucursales import service as sucursales_service
from app.modules.sucursales.models import Sucursal


class SaasServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.tablas = [
            Empresa.__table__, Plan.__table__, Rol.__table__, Proveedor.__table__,
            Sucursal.__table__, Usuario.__table__, LimitePlan.__table__,
            FuncionalidadPlan.__table__, Suscripcion.__table__,
            HistorialCambioPlan.__table__,
            Categoria.__table__, Talla.__table__, Color.__table__,
            Producto.__table__, ProductoVariante.__table__, Inventario.__table__,
            Promocion.__table__, PromocionProducto.__table__,
            PromocionVariante.__table__,
        ]
        SQLModel.metadata.create_all(self.engine, tables=self.tablas)
        self.session = Session(self.engine)
        self.super_rol = Rol(nombre=RolNombre.SUPERADMINISTRADOR)
        self.admin_rol = Rol(nombre=RolNombre.ADMINISTRADOR)
        self.session.add_all([self.super_rol, self.admin_rol])
        self.session.flush()
        self.superadmin = Usuario(
            nombre="Super", apellido="Admin", email="super@example.com",
            password_hash="no-usado", rol_id=self.super_rol.id,
        )
        self.plan = Plan(
            codigo="BASICO", nombre="Básico", descripcion="Plan de prueba",
            precio_mensual=Decimal("99.00"), activo=True,
        )
        self.session.add_all([self.superadmin, self.plan])
        self.session.flush()
        self.session.add_all([
            LimitePlan(plan_id=self.plan.id, codigo="MAX_SUCURSALES", valor_maximo=2),
            LimitePlan(plan_id=self.plan.id, codigo="MAX_USUARIOS", valor_maximo=10),
            FuncionalidadPlan(plan_id=self.plan.id, codigo="PWA_OFFLINE", habilitada=True),
        ])
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        SQLModel.metadata.drop_all(self.engine, tables=list(reversed(self.tablas)))

    def _registrar_empresa(self, identificador: str, email: str) -> Empresa:
        return saas_service.create_empresa(
            self.session,
            EmpresaCreate(
                identificador=identificador,
                nombre=identificador.replace("-", " ").title(),
                razon_social=f"{identificador} SRL",
                administrador=AdminInicialIn(
                    nombre="Ana", apellido="Admin", email=email,
                    password="Segura123!",
                ),
                plan_id=self.plan.id,
                fecha_inicio=date.today(),
                vigencia_meses=2,
            ),
            actor_id=self.superadmin.id,
        )

    def test_rutas_cu38_cu42_publicadas(self) -> None:
        paths = app.openapi()["paths"]
        for path in (
            "/empresas", "/empresas/{empresa_id}", "/planes",
            "/planes/{plan_id}", "/suscripciones", "/suscripciones/mi-plan",
        ):
            self.assertIn(path, paths)
        for path in (
            "/suscripciones/validar-cambio",
            "/suscripciones/cambiar-plan",
            "/suscripciones/historial",
            "/offline/preparar-datos",
        ):
            self.assertIn(path, paths)

    def test_cu06_idempotencia_y_cu07_compatibilidad(self) -> None:
        empresa = self._registrar_empresa("renovacion", "renueva@example.com")
        admin = self.session.exec(
            select(Usuario).where(Usuario.empresa_id == empresa.id)
        ).first()
        solicitud = CambioPlanIn(plan_id=self.plan.id, vigencia_meses=2)
        primero = saas_service.cambiar_o_renovar_plan(
            self.session,
            empresa.id,
            solicitud,
            actor_id=admin.id,
            clave_idempotencia="prueba-renovacion-0001",
        )
        repetido = saas_service.cambiar_o_renovar_plan(
            self.session,
            empresa.id,
            solicitud,
            actor_id=admin.id,
            clave_idempotencia="prueba-renovacion-0001",
        )
        self.assertFalse(primero.idempotente)
        self.assertTrue(repetido.idempotente)
        self.assertEqual(
            self.session.exec(
                select(func.count()).select_from(HistorialCambioPlan).where(
                    HistorialCambioPlan.clave_idempotencia
                    == "prueba-renovacion-0001"
                )
            ).one(),
            1,
        )

        plan_reducido = Plan(
            codigo="REDUCIDO",
            nombre="Reducido",
            precio_mensual=Decimal("50.00"),
            activo=True,
        )
        self.session.add(plan_reducido)
        self.session.flush()
        self.session.add(
            LimitePlan(
                plan_id=plan_reducido.id,
                codigo="MAX_USUARIOS",
                valor_maximo=0,
            )
        )
        self.session.commit()
        vista = saas_service.preview_cambio_plan(
            self.session,
            empresa.id,
            CambioPlanIn(plan_id=plan_reducido.id, vigencia_meses=1),
        )
        self.assertFalse(vista.compatible)
        self.assertEqual(vista.incompatibilidades[0].codigo, "MAX_USUARIOS")
        with self.assertRaises(HTTPException) as funcionalidad:
            saas_service.validar_acceso_plan(
                self.session,
                empresa.id,
                funcionalidad="FUNCIONALIDAD_NO_INCLUIDA",
            )
        self.assertEqual(funcionalidad.exception.status_code, 403)

    def test_cu09_payload_offline_aislado_por_sucursal(self) -> None:
        empresa = self._registrar_empresa("offline", "offline@example.com")
        admin = self.session.exec(
            select(Usuario).where(Usuario.empresa_id == empresa.id)
        ).first()
        sucursal = Sucursal(
            empresa_id=empresa.id,
            nombre="Centro",
            ciudad="Santa Cruz",
            direccion="Av. Centro",
        )
        categoria = Categoria(empresa_id=empresa.id, nombre="Offline")
        talla = Talla(empresa_id=empresa.id, valor="L", tipo="Ropa")
        color = Color(
            empresa_id=empresa.id, nombre="Azul offline", codigo_hex="#0000FF"
        )
        proveedor = Proveedor(
            empresa_id=empresa.id, nombre_empresa="Proveedor offline"
        )
        self.session.add_all([sucursal, categoria, talla, color, proveedor])
        self.session.flush()
        producto = Producto(
            empresa_id=empresa.id,
            nombre="Prenda offline",
            categoria_id=categoria.id,
            proveedor_id=proveedor.id,
            precio_base=Decimal("125.00"),
        )
        self.session.add(producto)
        self.session.flush()
        variante = ProductoVariante(
            empresa_id=empresa.id,
            producto_id=producto.id,
            talla_id=talla.id,
            color_id=color.id,
            sku="OFF-L-AZUL",
        )
        self.session.add(variante)
        self.session.flush()
        self.session.add(
            Inventario(
                variante_id=variante.id,
                sucursal_id=sucursal.id,
                cantidad_disponible=4,
                cantidad_reservada=1,
            )
        )
        self.session.commit()

        payload = offline_service.preparar_datos(
            self.session, admin, sucursal.id
        )
        self.assertEqual(payload.empresa_id, empresa.id)
        self.assertEqual(payload.sucursal_id, sucursal.id)
        self.assertEqual(payload.total_productos, 1)
        self.assertEqual(payload.productos[0].variantes[0].cantidad_disponible, 4)

    def test_cu38_registro_atomico_y_duplicado(self) -> None:
        empresa = self._registrar_empresa("moda-sur", "admin@modasur.example.com")
        salida = saas_service.to_empresa_out(self.session, empresa)
        self.assertEqual(salida.plan_nombre, "Básico")
        self.assertEqual(salida.suscripcion_estado, "ACTIVA")
        with self.assertRaises(HTTPException) as error:
            self._registrar_empresa("moda-sur", "otro@example.com")
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.session.exec(select(func.count()).select_from(Empresa)).one(), 1)
        self.assertEqual(self.session.exec(select(func.count()).select_from(Suscripcion)).one(), 1)

    def test_cu39_cu40_cu41_y_cu42(self) -> None:
        empresa = self._registrar_empresa("textil-norte", "admin@textil.example.com")
        plan = saas_service.update_plan(
            self.session, self.plan.id,
            PlanUpdate(
                precio_mensual=Decimal("109.50"),
                limites=[
                    LimitePlanIn(codigo="MAX_SUCURSALES", valor_maximo=3),
                    LimitePlanIn(codigo="MAX_USUARIOS", valor_maximo=12),
                ],
                funcionalidades=[FuncionalidadPlanIn(codigo="PWA_OFFLINE", habilitada=True)],
            ),
        )
        self.assertEqual(plan.precio_mensual, Decimal("109.50"))
        suspendida = saas_service.update_empresa(
            self.session, empresa.id, EmpresaUpdate(activa=False)
        )
        self.assertFalse(suspendida.activa)
        self.assertEqual(
            saas_service.to_empresa_out(self.session, suspendida).suscripcion_estado,
            "SUSPENDIDA",
        )
        saas_service.update_empresa(self.session, empresa.id, EmpresaUpdate(activa=True))
        saas_service.gestionar_suscripcion(
            self.session,
            SuscripcionGestionIn(
                empresa_id=empresa.id, plan_id=self.plan.id,
                fecha_inicio=date.today(), vigencia_meses=6, estado="ACTIVA",
                observacion="Renovación de prueba",
            ),
            actor_id=self.superadmin.id,
        )
        self.session.add(Sucursal(
            empresa_id=empresa.id, nombre="Centro", ciudad="Santa Cruz",
            direccion="Av. Principal",
        ))
        self.session.commit()
        resumen = saas_service.get_plan_consumo(self.session, empresa.id)
        consumos = {x.codigo: x for x in resumen.consumos}
        self.assertEqual(consumos["MAX_SUCURSALES"].utilizado, 1)
        self.assertEqual(consumos["MAX_USUARIOS"].utilizado, 1)
        self.assertEqual(resumen.suscripcion.estado, "ACTIVA")

        saas_service.update_plan(
            self.session,
            self.plan.id,
            PlanUpdate(
                limites=[
                    LimitePlanIn(codigo="MAX_SUCURSALES", valor_maximo=3),
                    LimitePlanIn(codigo="MAX_USUARIOS", valor_maximo=1),
                ]
            ),
        )
        with self.assertRaises(HTTPException) as limite:
            identidad_service.create_usuario(
                self.session,
                UsuarioCreate(
                    nombre="Segundo", apellido="Usuario",
                    email="segundo@example.com", password="Segura123!",
                    rol_id=self.admin_rol.id,
                ),
                empresa_id=empresa.id,
            )
        self.assertEqual(limite.exception.status_code, 409)

    def test_administrador_no_puede_cruzar_tenants(self) -> None:
        empresa_a = self._registrar_empresa("empresa-a", "admin@a.example.com")
        empresa_b = self._registrar_empresa("empresa-b", "admin@b.example.com")
        sucursal_b = Sucursal(
            empresa_id=empresa_b.id, nombre="Sucursal B", ciudad="La Paz",
            direccion="Calle B",
        )
        self.session.add(sucursal_b)
        self.session.commit()
        self.session.refresh(sucursal_b)
        usuarios, _ = identidad_service.list_usuarios(self.session, empresa_id=empresa_a.id)
        self.assertTrue(all(u.empresa_id == empresa_a.id for u in usuarios))
        sucursales, total = sucursales_service.list_sucursales(
            self.session, empresa_id=empresa_a.id
        )
        self.assertEqual(sucursales, [])
        self.assertEqual(total, 0)
        with self.assertRaises(HTTPException) as error:
            identidad_service.create_usuario(
                self.session,
                UsuarioCreate(
                    nombre="Usuario", apellido="Cruzado", email="cruzado@example.com",
                    password="Segura123!", rol_id=self.admin_rol.id,
                    sucursal_id=sucursal_b.id,
                ),
                empresa_id=empresa_a.id,
            )
        self.assertEqual(error.exception.status_code, 422)

    def test_catalogo_cliente_se_limita_a_su_empresa(self) -> None:
        empresa_a = self._registrar_empresa("catalogo-a", "catalogo-a@example.com")
        empresa_b = self._registrar_empresa("catalogo-b", "catalogo-b@example.com")
        sucursal_a = Sucursal(
            empresa_id=empresa_a.id, nombre="Sucursal A", ciudad="Santa Cruz",
            direccion="Calle A",
        )
        sucursal_b = Sucursal(
            empresa_id=empresa_b.id, nombre="Sucursal B", ciudad="La Paz",
            direccion="Calle B",
        )
        categoria_a = Categoria(empresa_id=empresa_a.id, nombre="Ropa")
        talla_a = Talla(empresa_id=empresa_a.id, valor="M", tipo="Ropa")
        color_a = Color(
            empresa_id=empresa_a.id, nombre="Negro", codigo_hex="#000000"
        )
        proveedor_a = Proveedor(
            empresa_id=empresa_a.id, nombre_empresa="Proveedor catálogo"
        )
        categoria_b = Categoria(empresa_id=empresa_b.id, nombre="Ropa")
        talla_b = Talla(empresa_id=empresa_b.id, valor="M", tipo="Ropa")
        color_b = Color(
            empresa_id=empresa_b.id, nombre="Negro", codigo_hex="#000000"
        )
        proveedor_b = Proveedor(
            empresa_id=empresa_b.id, nombre_empresa="Proveedor catálogo"
        )
        self.session.add_all([
            sucursal_a, sucursal_b,
            categoria_a, talla_a, color_a, proveedor_a,
            categoria_b, talla_b, color_b, proveedor_b,
        ])
        self.session.flush()
        producto_a = Producto(
            empresa_id=empresa_a.id, nombre="Producto A",
            categoria_id=categoria_a.id, proveedor_id=proveedor_a.id,
            precio_base=Decimal("100.00"),
        )
        producto_b = Producto(
            empresa_id=empresa_b.id, nombre="Producto B",
            categoria_id=categoria_b.id, proveedor_id=proveedor_b.id,
            precio_base=Decimal("120.00"),
        )
        self.session.add_all([producto_a, producto_b])
        self.session.flush()
        variante_a = ProductoVariante(
            empresa_id=empresa_a.id, producto_id=producto_a.id,
            talla_id=talla_a.id, color_id=color_a.id,
            sku="CAT-A-M-NEGRO",
        )
        variante_b = ProductoVariante(
            empresa_id=empresa_b.id, producto_id=producto_b.id,
            talla_id=talla_b.id, color_id=color_b.id,
            sku="CAT-B-M-NEGRO",
        )
        self.session.add_all([variante_a, variante_b])
        self.session.flush()
        self.session.add_all([
            Promocion(
                empresa_id=empresa_a.id, nombre="Promo A",
                tipo_descuento="PORCENTAJE", valor=Decimal("10"),
                fecha_inicio=date.today(), fecha_fin=date.today(),
            ),
            Promocion(
                empresa_id=empresa_b.id, nombre="Promo B",
                tipo_descuento="PORCENTAJE", valor=Decimal("10"),
                fecha_inicio=date.today(), fecha_fin=date.today(),
            ),
        ])
        self.session.add_all([
            Inventario(
                variante_id=variante_a.id, sucursal_id=sucursal_a.id,
                cantidad_disponible=5,
            ),
            Inventario(
                variante_id=variante_b.id, sucursal_id=sucursal_b.id,
                cantidad_disponible=7,
            ),
        ])
        self.session.commit()

        gestion_a, total_gestion_a = productos_service.list_productos(
            self.session, empresa_id=empresa_a.id
        )
        self.assertEqual(total_gestion_a, 1)
        self.assertEqual([item["nombre"] for item in gestion_a], ["Producto A"])
        categorias_a, total_categorias_a = catalogo_service.list_categorias(
            self.session, empresa_id=empresa_a.id
        )
        self.assertEqual(total_categorias_a, 1)
        self.assertEqual([item.nombre for item in categorias_a], ["Ropa"])
        proveedores_a, total_proveedores_a = proveedores_service.list_proveedores(
            self.session, empresa_id=empresa_a.id
        )
        self.assertEqual(total_proveedores_a, 1)
        self.assertEqual(
            [item.nombre_empresa for item in proveedores_a],
            ["Proveedor catálogo"],
        )
        self.assertEqual(
            [item["nombre"] for item in promociones_service.listar_promociones(
                self.session, empresa_id=empresa_a.id
            )],
            ["Promo A"],
        )
        self.assertEqual(
            [item.nombre for item in productos_service.productos_opciones(
                self.session, empresa_id=empresa_a.id
            )],
            ["Producto A"],
        )

        items_a, total_a = productos_service.list_catalogo(
            self.session, empresa_id=empresa_a.id
        )
        self.assertEqual(total_a, 1)
        self.assertEqual([item["nombre"] for item in items_a], ["Producto A"])
        candidatos_ia_a = ia_service._catalogo_para_ia(
            self.session, empresa_a.id
        )
        self.assertEqual(
            [producto.nombre for producto in candidatos_ia_a], ["Producto A"]
        )
        self.assertEqual(
            inventario_service.disponibilidad_variante(
                self.session, variante_b.id, empresa_id=empresa_a.id
            ),
            [],
        )
        with self.assertRaises(HTTPException) as detalle_cruzado:
            productos_service.get_catalogo_detalle(
                self.session, producto_b.id, empresa_id=empresa_a.id
            )
        self.assertEqual(detalle_cruzado.exception.status_code, 404)
        with self.assertRaises(HTTPException) as gestion_cruzada:
            productos_service.get_producto_detalle(
                self.session, producto_b.id, empresa_id=empresa_a.id
            )
        self.assertEqual(gestion_cruzada.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
