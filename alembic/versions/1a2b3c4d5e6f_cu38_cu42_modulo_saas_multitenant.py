"""CU38-CU42: módulo SaaS multitenant

Revision ID: 1a2b3c4d5e6f
Revises: 7281a3f79a54
Create Date: 2026-10-21

La migración conserva los datos previos dentro de una empresa heredada. Primero
agrega las FK como opcionales, rellena los registros y solo entonces hace
obligatoria la empresa de cada sucursal.
"""

from datetime import date, datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "7281a3f79a54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ahora = datetime.now(timezone.utc)

    op.create_table(
        "empresa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identificador", sqlmodel.sql.sqltypes.AutoString(50), nullable=False),
        sa.Column("nombre", sqlmodel.sql.sqltypes.AutoString(120), nullable=False),
        sa.Column("razon_social", sqlmodel.sql.sqltypes.AutoString(150), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_empresa_identificador", "empresa", ["identificador"], unique=True)
    op.create_index("ix_empresa_nombre", "empresa", ["nombre"], unique=False)
    op.create_index("ix_empresa_activa", "empresa", ["activa"], unique=False)

    empresa_tabla = sa.table(
        "empresa",
        sa.column("identificador", sa.String),
        sa.column("nombre", sa.String),
        sa.column("razon_social", sa.String),
        sa.column("activa", sa.Boolean),
        sa.column("fecha_registro", sa.DateTime(timezone=True)),
        sa.column("fecha_actualizacion", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        empresa_tabla,
        [
            {
                "identificador": "fashionstore-principal",
                "nombre": "FashionStore Principal",
                "razon_social": "FashionStore",
                "activa": True,
                "fecha_registro": ahora,
                "fecha_actualizacion": ahora,
            }
        ],
    )
    op.add_column("usuario", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.create_index("ix_usuario_empresa_id", "usuario", ["empresa_id"], unique=False)
    op.create_foreign_key(
        "fk_usuario_empresa_id", "usuario", "empresa", ["empresa_id"], ["id"]
    )
    op.add_column("sucursal", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.create_index("ix_sucursal_empresa_id", "sucursal", ["empresa_id"], unique=False)
    op.create_foreign_key(
        "fk_sucursal_empresa_id", "sucursal", "empresa", ["empresa_id"], ["id"]
    )
    op.execute(
        "UPDATE usuario SET empresa_id = "
        "(SELECT id FROM empresa WHERE identificador = 'fashionstore-principal')"
    )
    op.execute(
        "UPDATE sucursal SET empresa_id = "
        "(SELECT id FROM empresa WHERE identificador = 'fashionstore-principal')"
    )
    op.alter_column("sucursal", "empresa_id", existing_type=sa.Integer(), nullable=False)

    # Rol global. El primer Administrador existente se promueve para garantizar
    # acceso al nuevo panel sin crear credenciales ni tocar secretos.
    op.execute(
            "INSERT INTO rol (nombre) "
            "SELECT 'Superadministrador' "
            "WHERE NOT EXISTS (SELECT 1 FROM rol WHERE nombre = 'Superadministrador')"
    )
    op.execute(
        "UPDATE usuario SET "
        "rol_id = (SELECT id FROM rol WHERE nombre = 'Superadministrador'), "
        "empresa_id = NULL WHERE id = ("
        "SELECT u.id FROM usuario u JOIN rol r ON r.id = u.rol_id "
        "WHERE r.nombre = 'Administrador' ORDER BY u.id LIMIT 1)"
    )

    op.create_table(
        "plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sqlmodel.sql.sqltypes.AutoString(30), nullable=False),
        sa.Column("nombre", sqlmodel.sql.sqltypes.AutoString(60), nullable=False),
        sa.Column("descripcion", sqlmodel.sql.sqltypes.AutoString(300), nullable=True),
        sa.Column("precio_mensual", sa.Numeric(10, 2), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_codigo", "plan", ["codigo"], unique=True)
    op.create_index("ix_plan_activo", "plan", ["activo"], unique=False)
    op.create_table(
        "limite_plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sqlmodel.sql.sqltypes.AutoString(50), nullable=False),
        sa.Column("valor_maximo", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plan.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "codigo", name="uq_limite_plan_codigo"),
    )
    op.create_index("ix_limite_plan_plan_id", "limite_plan", ["plan_id"], unique=False)
    op.create_table(
        "funcionalidad_plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sqlmodel.sql.sqltypes.AutoString(50), nullable=False),
        sa.Column("habilitada", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plan.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_id", "codigo", name="uq_funcionalidad_plan_codigo"
        ),
    )
    op.create_index(
        "ix_funcionalidad_plan_plan_id", "funcionalidad_plan", ["plan_id"], unique=False
    )
    op.create_table(
        "suscripcion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("estado", sqlmodel.sql.sqltypes.AutoString(20), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plan.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suscripcion_empresa_id", "suscripcion", ["empresa_id"], unique=False)
    op.create_index("ix_suscripcion_plan_id", "suscripcion", ["plan_id"], unique=False)
    op.create_index("ix_suscripcion_estado", "suscripcion", ["estado"], unique=False)
    op.create_table(
        "historial_cambio_plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("suscripcion_id", sa.Integer(), nullable=False),
        sa.Column("plan_anterior_id", sa.Integer(), nullable=True),
        sa.Column("plan_nuevo_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo_cambio", sqlmodel.sql.sqltypes.AutoString(20), nullable=False),
        sa.Column("observacion", sqlmodel.sql.sqltypes.AutoString(255), nullable=True),
        sa.Column("fecha_cambio", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["suscripcion_id"], ["suscripcion.id"]),
        sa.ForeignKeyConstraint(["plan_anterior_id"], ["plan.id"]),
        sa.ForeignKeyConstraint(["plan_nuevo_id"], ["plan.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_historial_cambio_plan_suscripcion_id",
        "historial_cambio_plan",
        ["suscripcion_id"],
        unique=False,
    )

    plan_tabla = sa.table(
        "plan",
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
        sa.column("descripcion", sa.String),
        sa.column("precio_mensual", sa.Numeric),
        sa.column("activo", sa.Boolean),
        sa.column("fecha_creacion", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        plan_tabla,
        [
            {"codigo": "BASICO", "nombre": "Básico", "descripcion": "Operación esencial para tiendas pequeñas", "precio_mensual": 99, "activo": True, "fecha_creacion": ahora},
            {"codigo": "INTERMEDIO", "nombre": "Intermedio", "descripcion": "Más capacidad y reportes asistidos", "precio_mensual": 199, "activo": True, "fecha_creacion": ahora},
            {"codigo": "PROFESIONAL", "nombre": "Profesional", "descripcion": "Capacidad ampliada y todas las funciones SaaS", "precio_mensual": 349, "activo": True, "fecha_creacion": ahora},
        ],
    )
    for codigo, valores in {
        "BASICO": (2, 10, 0),
        "INTERMEDIO": (5, 30, 20),
        "PROFESIONAL": (10, 100, 100),
    }.items():
        for limite_codigo, valor in zip(
            ("MAX_SUCURSALES", "MAX_USUARIOS", "MAX_REPORTES_IA_MES"), valores
        ):
            op.execute(
                "INSERT INTO limite_plan (plan_id, codigo, valor_maximo) "
                f"SELECT id, '{limite_codigo}', {valor} FROM plan "
                f"WHERE codigo = '{codigo}'"
            )
    for codigo in ("BASICO", "INTERMEDIO", "PROFESIONAL"):
        for funcionalidad in (
            "PWA_OFFLINE",
            "REPORTES_CONVENCIONALES",
            "REPORTES_IA",
            "REPORTES_MULTISUCURSAL",
        ):
            habilitada = funcionalidad in ("PWA_OFFLINE", "REPORTES_CONVENCIONALES")
            if codigo in ("INTERMEDIO", "PROFESIONAL"):
                habilitada = True
            op.execute(
                "INSERT INTO funcionalidad_plan (plan_id, codigo, habilitada) "
                f"SELECT id, '{funcionalidad}', "
                f"{'TRUE' if habilitada else 'FALSE'} FROM plan "
                f"WHERE codigo = '{codigo}'"
            )

    op.execute(
        "INSERT INTO suscripcion "
        "(empresa_id, plan_id, fecha_inicio, fecha_vencimiento, estado, fecha_creacion, fecha_actualizacion) "
        "SELECT e.id, p.id, CURRENT_DATE, DATE '2099-12-31', 'ACTIVA', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
        "FROM empresa e CROSS JOIN plan p "
        "WHERE e.identificador = 'fashionstore-principal' AND p.codigo = 'PROFESIONAL'"
    )
    op.execute(
        "INSERT INTO historial_cambio_plan "
        "(suscripcion_id, plan_anterior_id, plan_nuevo_id, usuario_id, tipo_cambio, observacion, fecha_cambio) "
        "SELECT s.id, NULL, p.id, u.id, 'MIGRACION', "
        "'Suscripción heredada del primer parcial', CURRENT_TIMESTAMP "
        "FROM suscripcion s "
        "JOIN empresa e ON e.id = s.empresa_id "
        "JOIN plan p ON p.id = s.plan_id "
        "CROSS JOIN usuario u JOIN rol r ON r.id = u.rol_id "
        "WHERE e.identificador = 'fashionstore-principal' "
        "AND p.codigo = 'PROFESIONAL' AND r.nombre = 'Superadministrador' "
        "ORDER BY u.id LIMIT 1"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE usuario SET rol_id = (SELECT id FROM rol WHERE nombre = 'Administrador') "
        "WHERE rol_id IN (SELECT id FROM rol WHERE nombre = 'Superadministrador')"
    )

    op.drop_index("ix_historial_cambio_plan_suscripcion_id", table_name="historial_cambio_plan")
    op.drop_table("historial_cambio_plan")
    op.drop_index("ix_suscripcion_estado", table_name="suscripcion")
    op.drop_index("ix_suscripcion_plan_id", table_name="suscripcion")
    op.drop_index("ix_suscripcion_empresa_id", table_name="suscripcion")
    op.drop_table("suscripcion")
    op.drop_index("ix_funcionalidad_plan_plan_id", table_name="funcionalidad_plan")
    op.drop_table("funcionalidad_plan")
    op.drop_index("ix_limite_plan_plan_id", table_name="limite_plan")
    op.drop_table("limite_plan")
    op.drop_index("ix_plan_activo", table_name="plan")
    op.drop_index("ix_plan_codigo", table_name="plan")
    op.drop_table("plan")

    op.drop_constraint("fk_sucursal_empresa_id", "sucursal", type_="foreignkey")
    op.drop_index("ix_sucursal_empresa_id", table_name="sucursal")
    op.drop_column("sucursal", "empresa_id")
    op.drop_constraint("fk_usuario_empresa_id", "usuario", type_="foreignkey")
    op.drop_index("ix_usuario_empresa_id", table_name="usuario")
    op.drop_column("usuario", "empresa_id")
    op.execute("DELETE FROM rol WHERE nombre = 'Superadministrador'")
    op.drop_index("ix_empresa_activa", table_name="empresa")
    op.drop_index("ix_empresa_nombre", table_name="empresa")
    op.drop_index("ix_empresa_identificador", table_name="empresa")
    op.drop_table("empresa")
