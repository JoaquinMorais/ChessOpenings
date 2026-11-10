# Producto

## Concepto
El usuario arma un **repertorio de apertura** para un lado (blancas o negras), como un arbol de variantes, y despues lo **entrena**.

## Conceptos
- **Opening**: tiene nombre (ej. "Elephant Gambit") y color del usuario (`white` | `black`).
- **Lado del usuario**: el color del opening. **Lado rival**: el otro.
- **Arbol**: cada nodo es una posicion alcanzada por una jugada. El nodo raiz es la posicion inicial.
- **Rama**: en una posicion donde mueve el RIVAL puede haber varias jugadas hijas (varias respuestas buenas del rival). En una posicion donde mueve el USUARIO hay UNA sola jugada hija (su respuesta correcta). Esto se valida.
- **Linea principal**: la primera linea cargada. En cada nodo, el hijo con `order_index = 0` es la principal.
- Posiciones iguales alcanzadas por caminos distintos se **duplican** (no hay transposiciones). Es aceptado.

## Editor
- El usuario juega ambos lados en un tablero. Al jugar una jugada en una posicion:
  - si ya existe esa jugada como hijo, simplemente se navega a ella;
  - si no existe, se crea (si es turno del rival se agrega como nueva rama; si es turno del usuario y ya hay una jugada, se rechaza con mensaje claro).
- Se puede navegar el arbol, borrar una rama (con todo su subarbol) y marcar otra rama como principal (reordenar hermanas).

## Entrenamiento
Ver `docs/training-algorithm.md`. Resumen:
- La app juega el lado rival; el usuario responde con su lado.
- Siempre empieza por la linea principal; luego recorre el resto de las ramas en profundidad (DFS) sin saltar lejos entre ramas.
- Al cambiar de rama NO se repite desde el inicio: se salta (fast-forward) hasta el punto de bifurcacion.
- Si el usuario se equivoca: se le avisa, se le muestra la jugada correcta, NO puede reintentar en el momento. La posicion queda pendiente y se vuelve a preguntar mas tarde en la misma sesion.
- Termina cuando acerto todas las posiciones pendientes y se exploraron todas las ramas.
- Se guarda el porcentaje de acierto (por posicion y por opening).

## Persistencia, export/import
- Todo se guarda en PostgreSQL (volumen Docker).
- Export: archivo JSON versionado de un opening. Import: desde ese JSON en otra PC. Si ya existe un opening con el mismo nombre, se ofrece **reemplazar / duplicar / cancelar**.
- Las estadisticas NO se exportan en v1.
- Seed: `backend/data/seed.json` se importa al arrancar solo si la DB esta vacia (ver `utils/seed.py`).

## Fuera de alcance v1
Transposiciones, motor de ajedrez, usuarios/login, estadisticas avanzadas, repeticion espaciada.
