# store-backend

API REST de **FashionStore** — Plataforma Inteligente de Comercio Electrónico para tienda de ropa.
Examen 1 · Sistemas II · S2-2026 · Grupo 44 · UAGRM.

## Stack

- Python 3.12 + FastAPI
- SQLModel (ORM) + Alembic (migraciones)
- PostgreSQL (Neon)
- Autenticación JWT + bcrypt
- Despliegue en la nube (Render)

## Requisitos

- Python 3.12+
- Una base PostgreSQL (local o Neon)

## Puesta en marcha (desarrollo)

```bash
python -m venv venv
venv\Scripts\activate           # Windows
pip install -r requirements.txt
copy .env.example .env           # y completar DATABASE_URL, SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

La documentación interactiva queda en `http://localhost:8000/docs`.

## Estructura

```
app/
  core/      configuración, seguridad, dependencias
  models/    modelos SQLModel (tablas)
  schemas/   esquemas Pydantic (entrada/salida de la API)
  routers/   endpoints por dominio
  main.py    punto de entrada
alembic/     migraciones
```

## Repositorios del proyecto

- `store-backend` — este repo
- `store-frontend` — aplicación web (Angular)
- `store-movil` — aplicación móvil (Flutter)
