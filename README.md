# Chess Openings Trainer

Aplicación **local** para crear, entrenar, exportar e importar repertorios de aperturas de ajedrez. No usa cuentas, nube ni servicios externos: todo corre con Docker Compose y los datos quedan en un volumen local de PostgreSQL.

## Qué es

- Repertorios de aperturas para blancas o negras, organizados como un árbol de variantes.
- Editor de jugadas con tablero y panel de variantes.
- Entrenamiento guiado con repaso de errores, progreso y estadísticas.
- Exportación e importación de aperturas en JSON versionado para moverlas entre computadoras.
- Seed inicial con dos aperturas de ejemplo cuando la base está vacía.

## Requisitos

- Docker
- Docker Compose v2
- Puertos libres: `3000` (frontend) y `8000` (backend). PostgreSQL no se expone al host.

No hace falta tener Python, Node ni PostgreSQL instalados localmente.

## Cómo levantar

```bash
cp .env.example .env
docker compose up --build
```

`.env` no se versiona. Si ya existe, no hace falta volver a crearlo.

Servicios principales:

- `db`: PostgreSQL 16 con volumen `pgdata`.
- `backend`: FastAPI con el árbol de aperturas y el motor de entrenamiento.
- `frontend`: React + Vite servido por nginx, con proxy `/api` hacia el backend.

Al arrancar con una base vacía se carga `backend/data/seed.json`:

- Elephant Gambit (negras)
- Italian Game (blancas)

## URLs

- Aplicación: http://localhost:3000
- API: http://localhost:8000/api
- Documentación interactiva: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

## Cómo correr los tests

```bash
docker compose run --rm backend-test
```

Los tests usan `db-test`, una base PostgreSQL independiente y efímera, y no tocan la base de desarrollo.

> Nota: `docker compose run --rm backend pytest` quedó obsoleto como comando de tests. El servicio `backend` apunta a la base de desarrollo y la configuración de tests bloquea esa ejecución por seguridad. Usar siempre `backend-test`.

Build del frontend:

```bash
docker compose build frontend
```

## Exportar e importar entre PCs

1. En la lista de aperturas, usar **Exportar** en la apertura deseada.
2. Se descarga un archivo `<nombre>.json` con formato versionado.
3. En la otra computadora, usar **Importar** y elegir el archivo `.json`.
4. Si ya existe una apertura con ese nombre, la app ofrece:
   - **Reemplazar**: borra la existente y usa la importada.
   - **Duplicar**: crea una copia como `Nombre (2)`, `Nombre (3)`, etc.
   - **Cancelar**: no modifica nada.

Las estadísticas de entrenamiento no se exportan en esta versión.

## Estructura del repo

```text
backend/
  index.py        # app FastAPI, routers y lifespan
  config/         # settings y conexión a PostgreSQL
  data/seed.json  # aperturas iniciales
  models/         # modelos SQLModel
  routes/         # endpoints de openings, nodos, IO, entrenamiento y stats
  schemas/        # schemas de request/response
  tests/          # pytest
  utils/          # lógica de árbol, entrenamiento, seed, import/export y stats
frontend/
  src/api/        # cliente HTTP y funciones por recurso
  src/components/ # tablero, formularios, diálogos y árbol de variantes
  src/pages/      # lista, editor, entrenamiento y estadísticas
  src/types/      # tipos TypeScript
docs/             # producto, modelo de datos, arquitectura y algoritmo
docker-compose.yml
.env.example
```

## Comandos útiles

```bash
# Bajar la app manteniendo los datos
docker compose down

# Bajar la app y borrar la base de datos (el seed se recarga al arrancar)
docker compose down -v

# Bajar también los servicios de test (db-test) y limpiar la red
docker compose --profile test down -v

# Reconstruir y levantar todo
docker compose up --build
```
