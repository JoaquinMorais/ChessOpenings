# Convenciones

## Backend
- Type hints en todo. Funciones chicas. Rutas finas, logica en `utils/`.
- Un archivo de modelo, schema y route por entidad.
- Errores HTTP con `detail` en espanol claro (se muestran en la UI): 404 no existe, 409 conflicto, 422 validacion.
- Tests: cada endpoint tiene al menos camino feliz y un caso de error. La logica pura (arbol, entrenamiento, import) tiene tests unitarios sin DB.
- Fixtures en `tests/conftest.py` (sesion SQLite en memoria + TestClient).

## Frontend
- TypeScript estricto, sin `any`. Componentes funcionales con hooks.
- Cliente HTTP unico en `src/api/`. Tipos en `src/types/`.
- Todos los textos visibles en espanol. Estados de carga y error siempre visibles.

## Git
- Un commit por historia. Mensaje: `feat(us-XX): resumen corto`.
