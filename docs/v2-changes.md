# Cambios de la v2 (fuente de verdad para las historias V2-xx)

Esto AMPLIA los otros docs; si hay contradiccion, manda este archivo.

## Migraciones
- Desde V2-01 el esquema se maneja con **Alembic** (ya no `create_all`). El backend ejecuta `alembic upgrade head` al arrancar, antes del seed.
- Una DB creada con la v1 (por `create_all`) debe seguir funcionando: la migracion baseline crea solo las tablas que no existan.

## Nodos: nombre y observaciones
- `Node.name`: texto opcional (max 80). Nombre de la rama/variante (ej. "Variante Alapin").
- `Node.comment`: texto largo opcional (observaciones libres).
- `PATCH /api/nodes/{node_id}` {name?, comment?, classification?}. String vacio o null = borrar. Solo se actualizan los campos enviados.
- El arbol (`GET /tree`) incluye `name`, `comment` y `classification` en cada nodo.
- Export/import: cada nodo del JSON puede incluir `name`, `comment` y `classification` (opcionales). `version` sigue en 1; los archivos viejos sin esos campos siguen importando.

## Clasificacion de jugadas (estilo chess.com)
- Es **manual**: la elige el usuario, no hay motor. Se guarda en `Node.classification` (nullable) y describe la jugada que llevo a ese nodo. No aplica a la raiz.
- Se puede clasificar tanto jugadas propias como del rival (ej. una jugada del rival marcada como "Error" es una trampa o respuesta floja que el usuario quiere saber castigar).
- No afecta la logica de entrenamiento ni las reglas del arbol: es solo informacion.
- Valores validos (clave interna en ingles, snake_case):

| clave | etiqueta (UI) | simbolo | color aprox. |
|---|---|---|---|
| brilliant | Brillante | !! | #1baca6 |
| great | Gran jugada | ! | #5c8bb0 |
| best | Mejor jugada | ★ | #96bc4b |
| excellent | Excelente | ✓ | #81b64c |
| good | Buena | • | #a0b090 |
| book | De libro | B | #a88865 |
| inaccuracy | Imprecision | ?! | #f7c631 |
| mistake | Error | ? | #e58f2a |
| miss | Oportunidad perdida | ✗ | #ff7769 |
| blunder | Error grave | ?? | #ca3431 |

- La lista vive en UN solo lugar por capa: un Enum en `backend/models/` (o `schemas/`) y una constante en `frontend/src/types/` con clave, etiqueta, simbolo y color. Agregar o quitar una clasificacion debe ser tocar solo esos dos lugares (+ migracion si la columna es enum de DB; preferir columna string validada en el schema para evitar migraciones al cambiar la lista).
- Clasificacion invalida -> 422.

## Seed manual (`seed_import`)
- Carpeta `backend/data/seed_import/`, **un archivo .json por opening** (mismo formato del export, `<slug-del-nombre>.json`).
- `docker-compose.yml` monta `./backend/data:/app/data` en el servicio backend para que los archivos queden en el repo/host y sobrevivan a borrar la DB.
- Reglas de carga al arrancar (en `utils/seed.py`, despues de migraciones):
  1. `data/seed.json`: igual que antes, solo si la DB esta vacia.
  2. `data/seed_import/*.json`: por cada archivo, si NO existe un opening con ese nombre, se importa. Si existe, se ignora (nunca pisa lo que el usuario tiene en DB). Un archivo invalido se loguea y se saltea sin frenar el arranque.
- Endpoints:
  - `POST /api/openings/{id}/seed`: escribe/sobrescribe el archivo del opening (export actual).
  - `DELETE /api/openings/{id}/seed`: borra el archivo.
  - `GET /api/openings` suma `in_seed: bool` (hay archivo con su nombre).
- Borrar un opening que esta en seed_import hace que reaparezca al reiniciar: la UI debe preguntar si tambien se quita del seed.

## Reglas del tablero (editor y entrenamiento)
- Componente unico reutilizable de tablero para ambas pantallas.
- Al seleccionar una pieza (click o inicio de arrastre) se muestra un **punto** en cada casilla legal de destino (anillo si es captura). Al seleccionar otra pieza, los puntos pasan a ser los de la nueva. Soltar en casilla ilegal no hace nada y limpia o actualiza la seleccion; nunca quedan puntos viejos.
- Se puede mover tambien con click en pieza y click en destino.
- Ultima jugada resaltada en **amarillo** en las casillas origen y destino. En el editor sale del nodo actual (al navegar se actualiza; en la raiz no hay resaltado).
- Si la jugada actual tiene clasificacion, se muestra su icono (simbolo + color) en la casilla destino de la ultima jugada, como en chess.com. Si la version de react-chessboard no permite dibujarlo sobre la casilla, mostrarlo junto a la info de la jugada.
- Deben funcionar: captura al paso (en passant), enroque corto y largo, y promocion (con selector de pieza; por defecto reina si no hay selector).
