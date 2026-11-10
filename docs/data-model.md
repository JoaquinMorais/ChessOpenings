# Modelo de datos

## Tablas (SQLModel)
**Opening**: `id`, `name` (unico), `color` ('white'|'black'), `created_at`, `updated_at`.

**Node**: `id`, `opening_id` (FK, cascade), `parent_id` (FK a Node, null solo en la raiz), `move_san`, `move_uci` (null en la raiz), `fen` (posicion DESPUES de la jugada), `ply` (0 en la raiz), `order_index` (0 = principal entre hermanas), `comment` (opcional).
- Cada opening tiene exactamente 1 nodo raiz (ply 0, FEN inicial).
- Unico (`parent_id`, `move_uci`).
- Regla: si en `parent` le toca mover al usuario, solo puede tener 1 hijo. Si le toca al rival, puede tener N.
- Borrado en cascada del subarbol.

**TrainingSession**: `id`, `opening_id`, `started_at`, `finished_at` (null), `questions_total`, `first_try_correct`, `state` (JSON con el plan y pendientes).

**PositionStat**: `id`, `node_id` (la posicion donde el usuario debe mover; FK cascade), `attempts`, `correct`, `last_practiced_at`. Unico por `node_id`.

Porcentaje de acierto = `correct / attempts * 100`. Por opening = suma de sus PositionStat.

## Formato de export/import (JSON versionado)
```json
{
  "format": "chess-openings-trainer",
  "version": 1,
  "opening": {
    "name": "Elephant Gambit",
    "color": "black",
    "tree": {
      "children": [
        { "san": "e4", "comment": null, "children": [
          { "san": "e5", "children": [
            { "san": "Nf3", "children": [ { "san": "d5", "children": [] } ] }
          ]}
        ]}
      ]
    }
  }
}
```
- `tree` es la raiz implicita (posicion inicial); `children` ordenados: el primero es la principal.
- Se usa SAN; al importar se recalculan `uci`, `fen` y `ply` con python-chess y se valida legalidad y la regla de 1 hijo en turno del usuario. Error claro indicando la ruta de la jugada invalida.
- `version` desconocida -> error 422. Los archivos de `data/seed.json` usan este mismo formato (puede ser una lista de aperturas con el mismo shape bajo la clave `openings`).
