# Algoritmo de entrenamiento

Debe vivir como logica PURA y testeable en `backend/utils/training.py` (sin FastAPI ni DB dentro).

## Definiciones
- **Pregunta**: nodo donde le toca mover al usuario y que tiene un hijo (la jugada correcta). Se identifica por su `node_id`.
- **Orden de recorrido**: DFS desde la raiz. En cada nodo, hijos ordenados con la principal (`order_index = 0`) primero; las demas hermanas se mezclan aleatoriamente entre si. Nunca se mezcla entre niveles: eso garantiza que no se salte de 1.1.3.1 a 1.6.2.3.

## Fase 1: recorrido
1. Se visita cada nodo una sola vez. Nodos del rival: la app juega la jugada (el usuario la ve). Nodos de pregunta: se le pregunta al usuario.
2. Al terminar una linea (hoja), la siguiente continua desde el punto de bifurcacion mas profundo que aun tenga hermanas sin visitar. Las jugadas hasta ahi se muestran en **fast-forward** (sin preguntar, ya fueron respondidas).
3. Respuesta correcta: se registra acierto y se sigue.
4. Respuesta incorrecta: se informa, se muestra la jugada correcta, se juega esa jugada y se sigue por la rama (no hay reintento inmediato). La pregunta se agrega a `pendientes`.

## Fase 2: repaso
Cuando termina la fase 1, si hay pendientes se repasan en orden DFS. Para cada una se muestra el camino desde la raiz en fast-forward y se vuelve a preguntar (sin recorrer lo que sigue). Si falla otra vez, sigue pendiente para la ronda siguiente. Se repiten rondas hasta que no queden pendientes.

## Fin
La sesion termina (`finished_at`) cuando no quedan nodos sin visitar ni pendientes.

## Estadisticas
- Cada respuesta (fase 1 y repaso) incrementa `attempts` y, si es correcta, `correct` en `PositionStat` del nodo.
- La sesion guarda `questions_total` y `first_try_correct`.

## Forma de un paso devuelto al frontend
```json
{
  "kind": "question",            // o "finished"
  "node_id": 42,                 // posicion donde debe mover el usuario
  "fen": "...",                  // posicion de la pregunta
  "lead_in": [                   // jugadas a reproducir antes de preguntar
    {"uci": "e2e4", "san": "e4", "fast_forward": false}
  ],
  "phase": "traversal",          // o "review"
  "progress": {"answered": 3, "total": 12, "pending": 1}
}
```
En `finished`: incluye resumen {questions_total, first_try_correct, accuracy}.
