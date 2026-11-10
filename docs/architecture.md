# Arquitectura

## Servicios (docker-compose.yml)
- `db`: `postgres:16-alpine`, volumen `pgdata`, healthcheck.
- `backend`: FastAPI con uvicorn, depende de `db` (healthy). Puerto interno 8000.
- `frontend`: build de Vite servido por nginx; `/api/*` proxy a `backend:8000`. Expuesto en `http://localhost:3000`.
- Variables en `.env` (con `.env.example` versionado).

## Backend (`backend/`)
```
index.py     # crea la app, incluye routers, lifespan: create_all + seed si DB vacia
config/      # settings.py (pydantic-settings), database.py (engine, get_session)
data/        # seed.json
models/      # opening.py, node.py, training.py (SQLModel table=True)
routes/      # openings.py, nodes.py, io.py, training.py, stats.py
schemas/     # *_schema.py (request/response)
tests/       # pytest; DB SQLite en memoria via override de get_session
utils/       # seed.py, tree.py, opening_io.py, training.py (motor puro)
```
- Sin Alembic en v1: `SQLModel.metadata.create_all` al arrancar.
- Validacion de jugadas con `python-chess` (el backend es la fuente de verdad de la legalidad).
- Prefijo de todas las rutas: `/api`.

## Endpoints (contrato objetivo)
Openings
- `GET /api/openings` lista con resumen (nombre, color, cantidad de nodos, % de acierto)
- `POST /api/openings` {name, color}
- `GET /api/openings/{id}` ; `PATCH /api/openings/{id}` {name} ; `DELETE /api/openings/{id}`
- `GET /api/openings/{id}/tree` arbol completo anidado

Nodos
- `POST /api/openings/{id}/moves` {parent_id, move (UCI o SAN)} -> crea nodo o devuelve el existente
- `DELETE /api/nodes/{node_id}` borra el subarbol (no se puede borrar la raiz)
- `POST /api/nodes/{node_id}/make-main` lo pone como `order_index = 0` entre hermanas

Import/Export
- `GET /api/openings/{id}/export` descarga JSON
- `POST /api/openings/import?on_conflict=reject|replace|duplicate` con el JSON. Con `reject` y nombre existente -> 409.

Entrenamiento
- `POST /api/training/sessions` {opening_id} -> sesion + primer paso
- `POST /api/training/sessions/{id}/answer` {node_id, move} -> {correct, correct_move_san, next_step}
- `GET /api/training/sessions/{id}`
- `GET /api/openings/{id}/stats` accuracy del opening y por posicion

## Frontend (`frontend/src/`)
```
api/ pages/ components/ hooks/ types/
```
Paginas: Lista de openings, Editor, Entrenar, Estadisticas. Textos en espanol. Router: react-router.
El tablero usa `react-chessboard`; `chess.js` valida movimientos en el cliente (el backend valida igual).
