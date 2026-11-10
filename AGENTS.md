# Chess Openings Trainer

App **local** para crear, entrenar, exportar e importar repertorios de aperturas de ajedrez.
Todo corre con `docker compose up`. Lee los archivos de `docs/` antes de empezar cualquier tarea.

## Stack
- Backend: Python 3.12, FastAPI, SQLModel, PostgreSQL 16 (`postgres:16-alpine`), python-chess, pytest.
- Frontend: React + Vite + TypeScript, `react-chessboard`, `chess.js`. Servido por nginx con proxy `/api` -> backend.
- Infra: Docker Compose (servicios: `db`, `backend`, `frontend`; tests: `backend-test`).

## Estructura del repo
```
backend/
  index.py        # app FastAPI (entrypoint)
  config/         # settings, conexion a DB
  data/           # seed.json (seed inicial)
  models/         # modelos SQLModel (tablas)
  routes/         # routers FastAPI
  schemas/        # schemas Pydantic/SQLModel de request/response
  tests/          # pytest
  utils/          # logica reutilizable (seed.py, arbol, entrenamiento, import/export)
frontend/
docs/
docker-compose.yml
```

## Reglas de trabajo (IMPORTANTE)
1. Trabaja SOLO en la historia de usuario que te pase. No adelantes otras ni refactorices lo que no se pide.
2. Antes de escribir codigo, resume en 3-5 lineas que vas a hacer. Si algo contradice `docs/`, avisame en vez de improvisar.
3. No agregues dependencias nuevas sin decirlo explicitamente y justificarlo.
4. Cada historia termina con: tests pasando (`docker compose run --rm backend-test` para backend) y la app levantando. Reporta el resultado real de los comandos, no lo supongas.
5. La logica de negocio vive en `utils/`, las rutas solo validan, llaman y responden.
6. Codigo, nombres, commits y comentarios en ingles. **Textos de la interfaz en espanol.**
7. No toques `docs/` ni `AGENTS.md` salvo que la historia lo pida.
8. Al terminar, lista los archivos creados/modificados y como probar a mano.
9. Nada de autenticacion, nube ni multiusuario: es una app local.

## Comandos
- Levantar todo: `docker compose up --build`
- Tests backend: `docker compose run --rm backend-test`
- Build frontend: `cd frontend && npm run build`
