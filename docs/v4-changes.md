# Cambios de la v4 (fuente de verdad para las historias V4-xx)

Esto AMPLIA y en algunos puntos REEMPLAZA lo de v2-changes.md (seccion Seed manual) y v3-changes.md; si hay contradiccion, manda este archivo.

## Seed: estructura nueva (publico / privado)
- `backend/data/seed_import/public/*.json`: se versiona en git (cualquiera que clone el repo los recibe).
- `backend/data/seed_import/private/*.json`: NUNCA va a git. Es el repertorio personal.
- Se elimina `backend/data/seed.json`: sus openings pasan a archivos individuales en `public/`. Se elimina tambien la regla "solo si la DB esta vacia".
- Un archivo por opening, nombre = slug del nombre del opening, contenido = mismo formato del export (version 1).
- Proteccion de privacidad en capas (todas obligatorias):
  1. `backend/data/seed_import/private/.gitignore` con `*`, `!.gitignore` y `!.gitkeep` (viaja con la carpeta, funciona aunque falte el .gitignore de la raiz). El backend lo crea si no existe ANTES de escribir cualquier archivo en `private/`.
  2. `.gitignore` de la raiz ignora `backend/data/seed_import/private/*` (salvo `.gitkeep`) y `backend/data/local/`.
  3. `.dockerignore` del backend excluye `data/seed_import/private/` y `data/local/` para que no queden dentro de la imagen.
- Visibilidad de un opening = `public` | `private` | ninguna (solo existe en la base). Se DERIVA de los archivos existentes, no es una columna. Un opening solo puede estar en una carpeta: cambiar la visibilidad mueve el archivo.
- Colisiones de nombre entre archivos: se cargan primero los de `private/`; si otro archivo tiene el mismo nombre de opening se saltea con una advertencia.

## Carga al arrancar y registro (tabla `SeedImport`)
- Tabla `seed_import`: `id`, `file_key` (unico, ej. `public/ruy-lopez-apertura-espanola.json`), `name`, `content_hash`, `imported_at`. Migracion de Alembic.
- Al arrancar (despues de las migraciones), para cada archivo de `private/` y luego de `public/`:
  - si su `file_key` NO esta en la tabla: se importa (si ya hay un opening con ese nombre en la DB no se toca, solo se registra) y se registra;
  - si ya esta registrado: no se hace nada, aunque el opening ya no exista en la DB (borrado local) y aunque el archivo haya cambiado.
- Consecuencias buscadas: volumen/DB nueva -> se importa todo; reinicio normal -> NO resucita lo borrado localmente; archivo nuevo traido con git pull -> se importa en el proximo arranque.
- Guardar un opening en el seed registra o actualiza su `file_key` con el hash nuevo.
- Archivo invalido: log de advertencia y se saltea, sin frenar el arranque.

## Guardar en seed
- `POST /api/openings/{id}/seed` body `{visibility: "public"|"private", evaluate?: bool, allow_external?: bool}`: escribe el archivo de forma atomica (temporal + rename), borra el archivo de la otra carpeta si existia, actualiza el registro. Si `evaluate` es true inicia el job de valoracion (ver mas abajo) y devuelve `job_id`.
- `GET /api/openings` suma `seed_visibility: "public"|"private"|null`. (`in_seed` queda como `seed_visibility != null`.)

## Borrado con alcance
- `DELETE /api/openings/{id}?scope=local|seed|both`:
  - `local`: borra de la DB; deja el archivo y el registro. No vuelve en reinicios; vuelve con DB nueva o con "Restaurar".
  - `seed`: borra archivo y registro; el opening sigue en la DB (queda solo local).
  - `both`: ambas.
  - Si el opening no tiene archivo, `scope` se ignora (se borra de la DB). Si tiene archivo y no se manda `scope`: 422.
- Borrar del seed un archivo `private` es irreversible (no esta en git): la UI pide escribir el nombre del opening para confirmar.
- Restaurar: `GET /api/seed/files` -> `[{file_key, name, visibility, state}]` con `state` = `in_db` | `deleted_locally` | `new`; `POST /api/seed/restore {file_key}` importa ese archivo a la DB (409 si ya hay un opening con ese nombre).

## Favoritos
- `Opening.is_favorite` (bool, default false). `POST /api/openings/{id}/favorite {value: bool}`.
- `GET /api/openings`: favoritos primero, luego por nombre (sin distinguir mayusculas), orden estable. Todo selector de openings para entrenar usa el mismo orden.
- Persistencia local: `backend/data/local/favorites.json` (lista de nombres), ignorado por git; se escribe en cada cambio y se aplica al arrancar, despues de cargar el seed. Los favoritos NO viajan dentro de los archivos de seed.

## Valoracion automatica de posiciones
- Interfaz `Evaluator` (en `backend/utils/evaluators/`): `evaluate(fen) -> {cp}|{mate}` desde la perspectiva de las blancas (mismo formato de `evaluation` de la v3). Implementaciones:
  - `stockfish` (por defecto): motor local con python-chess, sin red, instalado en la imagen Docker del backend.
  - `llm` (opcional): API compatible con OpenAI configurable.
- `evaluation` suma la clave opcional `source`: `manual` | `engine` | `llm` (en la API, en el export/import y en el arbol). Si falta se asume `manual`. Editar una valoracion a mano (PATCH) la deja como `manual`.
- Solo se valoran los nodos SIN evaluacion: nunca se pisa una valoracion existente. Es idempotente: si no falta ninguna, no se hace nada (la UI muestra "ya valorada"); si se agregan ramas nuevas, solo se valoran esas.
- Job asincrono: 1 por opening a la vez (409 si ya corre), progreso, cancelable, guarda cada resultado en la DB apenas lo obtiene (si se corta, lo hecho queda). Al terminar, si el opening esta en el seed, reescribe su archivo.
  - `GET /api/openings/{id}/evaluation-status` -> `{total, missing, running, job_id|null}`
  - `GET /api/jobs/{job_id}` -> `{state: running|done|cancelled|error, done, total, errors, message}`
  - `POST /api/jobs/{job_id}/cancel`
- Configuracion por variables de entorno (agregar a `.env.example` y al compose): `EVALUATOR=stockfish|llm`, `STOCKFISH_PATH=/usr/games/stockfish`, `EVAL_MOVETIME_MS=300`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_MIN_INTERVAL_S`.
- Privacidad: el evaluator `llm` envia posiciones a un tercero. Para openings `private` exige `allow_external=true` explicito en el POST (la UI avisa); sin eso responde 409. El evaluator `stockfish` no tiene esa restriccion.
- Advertencia de calidad: las valoraciones de un LLM son poco confiables (no calculan tacticas). La UI muestra la procedencia (motor / IA / manual) junto a la valoracion.