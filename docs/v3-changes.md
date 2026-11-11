# Cambios de la v3 (fuente de verdad para las historias V3-xx)

Esto AMPLIA los otros docs (incluido v2-changes.md); si hay contradiccion, manda este archivo.

## Evaluacion de posiciones (manual)
- Es **manual**: la carga el usuario, no hay motor. Representa cuanto vale la posicion resultante de la jugada de un nodo.
- Siempre desde la perspectiva de las **blancas** (positivo = ventaja blanca, negativo = ventaja negra), como en cualquier motor o en chess.com.
- Se guarda en `Node.eval_cp` (int, centipeones, nullable) y `Node.eval_mate` (int, nullable; positivo = mate de blancas en N, negativo = mate de negras en N). Solo uno de los dos puede estar seteado.
- En la API se expone como un unico campo `evaluation`: `{"cp": 35}` | `{"mate": 3}` | `null`.
- Validacion: exactamente una de las dos claves; `cp` entero en [-9999, 9999]; `mate` entero distinto de 0 con |mate| <= 99. Si no, 422 con detail en espanol.
- Se puede evaluar CUALQUIER nodo, **incluida la raiz** (a diferencia de name/comment/classification, que en la raiz dan 409).
- `PATCH /api/nodes/{node_id}` acepta `evaluation` (objeto, o `null` para borrar). Solo se actualizan los campos enviados (usar `model_fields_set`).
- `GET /tree` incluye `evaluation` en cada nodo. Export/import: clave opcional `evaluation` con el mismo formato (`{"cp": 35}` o `{"mate": 3}`); archivos sin ella importan igual. `version` sigue en 1.
- No afecta reglas del arbol ni el algoritmo de entrenamiento: es solo informacion.

## Entrada y formato (frontend, `src/utils/evaluation.ts`)
- `parseEvaluation(text)`: acepta `0.35`, `+0.35`, `-1,2` (coma decimal), `=` y `0` (igualdad = cp 0), mate como `#3`, `M3`, `-#2`, `#-2`, `-M2`. Vacio -> null (borrar). Invalido -> error con mensaje en espanol. Valores en peones; cp = round(peones * 100). Maximo +-99.99 peones.
- `formatEvaluation(ev)`: `+0.35`, `-1.20`, `0.00`, mate como `M3` / `-M3`.
- Presets rapidos (perspectiva blancas):

| boton | significado | cp |
|---|---|---|
| = | Igualdad | 0 |
| ⩲ | Blancas ligeramente mejor | +50 |
| ± | Blancas mejor | +100 |
| +- | Blancas ganando | +300 |
| ⩱ | Negras ligeramente mejor | -50 |
| ∓ | Negras mejor | -100 |
| -+ | Negras ganando | -300 |

## Barra de evaluacion (estilo chess.com)
- Barra vertical a la **izquierda del tablero**, misma altura que el tablero, en el editor y en el entrenamiento.
- Zona blanca y zona negra. Con el tablero orientado para blancas, las blancas van abajo; si el tablero esta volteado (usuario con negras), la barra tambien se voltea.
- Porcentaje de la zona blanca: `100 / (1 + exp(-0.00368208 * cp))`. Mate de blancas = 100%, mate de negras = 0%. Sin evaluacion = 50% con aspecto apagado y tooltip "Sin evaluacion".
- Etiqueta numerica (formatEvaluation) en el extremo de la zona que va ganando (abajo si ventaja blanca con blancas abajo; arriba si ventaja negra). En igualdad, en el extremo de las blancas. Texto con contraste adecuado sobre cada zona.
- Transicion suave (~300ms). Tooltip con el texto completo: "Evaluacion: +0.35 (ventaja de las blancas)".
- Colores aprox.: zona blanca #f2f2f2, zona negra #403d39, bordes redondeados chicos. Debe verse bien en modo oscuro.

## Evaluacion en el entrenamiento
- La barra muestra la evaluacion de la posicion que se ve en el tablero: durante `lead_in` se actualiza jugada a jugada; en una pregunta muestra la evaluacion de la posicion de la pregunta (no es spoiler); despues de responder pasa a la evaluacion de la posicion tras la jugada correcta.
- Nunca se muestra la evaluacion ni la clasificacion de la jugada correcta del usuario antes de que responda.
- Ajustes persistentes en localStorage, ambos activos por defecto: "Mostrar evaluacion" y "Mostrar clasificaciones".

## Insignia de clasificacion en el tablero (estilo chess.com)
- Circulo de color (el de la tabla de clasificaciones de v2-changes.md) con el simbolo en blanco, en la esquina **superior derecha de la casilla destino** de la ultima jugada, **un poco metido dentro de la casilla** (no centrado sobre la esquina ni afuera).
- Se hace como **overlay propio** sobre el tablero (capa absoluta con `pointer-events: none`, celdas calculadas en porcentajes segun la orientacion), no dependiendo de la API de la version de react-chessboard.
- Medidas guia (relativas a la casilla): diametro ~38%, `top` ~6%, `right` ~6%; sombra suave; simbolo en negrita (con tamano menor para `!!`, `??`, `?!`); animacion de aparicion corta (~140ms).
- Se usa igual en el editor y en el entrenamiento. Reemplaza cualquier insignia anterior del tablero (no duplicar).
- La insignia de la jugada del usuario en entrenamiento solo aparece despues de responder.

## Datos extra en los pasos de entrenamiento
- Cada item de `lead_in` suma `evaluation` y `classification` (y `name`) del nodo resultante.
- El paso `question` suma `evaluation` de la posicion de la pregunta.
- La respuesta de `/answer` incluye `correct_move: {uci, san, name, comment, classification, evaluation}`.
