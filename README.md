# store-backend

API REST de **FashionStore** — Plataforma Inteligente de Comercio Electrónico para tienda de ropa.
Examen 1 · Sistemas II · S2-2026 · Grupo 44 · UAGRM.

## Stack

- Python 3.12 + FastAPI
- SQLModel (ORM) + Alembic (migraciones)
- PostgreSQL (Neon)
- Autenticación JWT + bcrypt
- Despliegue en la nube (Render)

## Puesta en marcha (desarrollo)

```bash
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          REM completar DATABASE_URL y SECRET_KEY
alembic upgrade head            REM crea las tablas en la base
python -m app.seed              REM roles + usuario administrador
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Documentación interactiva (Swagger): `http://localhost:8000/docs`
- Admin inicial: `admin@fashionstore.com` / `Admin123!` (configurable en `.env`)

## Estructura

```
app/
  core/                configuración transversal
    config.py            variables de entorno
    db.py                motor + sesión de BD
    security.py          hash de contraseñas + JWT
    deps.py              dependencias: sesión, usuario actual, control de roles
  modules/             un paquete por dominio (= paquetes de casos de uso)
    identidad/           Rol, Usuario, autenticación
      models.py            tablas SQLModel
      schemas.py           entrada/salida de la API (Pydantic)
      service.py           lógica de negocio
      router.py            endpoints
  db_models.py          importa todos los modelos (lo usa Alembic)
  seed.py               datos iniciales
  main.py               crea la app y engancha los routers
alembic/               migraciones de base de datos
```

Cada endpoint lleva un comentario `# CUnn` que lo liga a su caso de uso.

## Migraciones

```bash
alembic revision --autogenerate -m "modulo: descripcion del cambio"
alembic upgrade head          # aplicar
alembic downgrade -1          # revertir la última
```

## Repositorios del proyecto

- `store-backend` — este repo
- `store-frontend` — aplicación web (Angular + Material + Tailwind)
- `store-movil` — aplicación móvil (Flutter)
