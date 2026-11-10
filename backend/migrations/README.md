# Migraciones

El backend aplica automáticamente `alembic upgrade head` al arrancar, antes de cargar el seed.

## Crear una migración nueva

Desde la raíz del repositorio:

```bash
docker compose run --rm -v "$PWD/backend:/app" backend alembic revision --autogenerate -m "descripcion del cambio"
```

El volumen es necesario para que el archivo generado quede en `backend/migrations/versions/`.

## Aplicar migraciones manualmente

```bash
docker compose run --rm -v "$PWD/backend:/app" backend alembic upgrade head
```

## Notas

- `migrations/env.py` usa `config.database.engine` y `SQLModel.metadata`.
- La migración `0001_baseline` usa el inspector de SQLAlchemy: crea solo las tablas que no existen, por lo que es segura para bases creadas con `create_all` en la v1.
- Los tests no usan Alembic: `tests/conftest.py` crea el esquema con `SQLModel.metadata.create_all`.
