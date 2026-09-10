"""Punto único de importación de TODOS los modelos.

Alembic importa este módulo para poblar `SQLModel.metadata` y detectar cambios.
Cada vez que se agrega un módulo con tablas nuevas, se agrega su import acá.
"""

from app.modules.identidad import models as identidad  # noqa: F401
from app.modules.proveedores import models as proveedores  # noqa: F401
from app.modules.sucursales import models as sucursales  # noqa: F401
