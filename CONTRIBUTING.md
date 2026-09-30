# Guía de Contribución y Trazabilidad Git (CreewLoop)

¡Gracias por contribuir a **CreewLoop**! Para mantener un historial de Git ordenado, semántico y completamente rastreable, este proyecto se rige por las siguientes directivas de control de versiones.

---

## 1. Estrategia de Ramas (Branching Model)

Todo desarrollo debe realizarse sobre una rama dedicada creada a partir de la rama principal (`main` o `develop`):

- **Nuevas funcionalidades**: `feat/<nombre-funcionalidad>`
- **Corrección de errores**: `fix/<identificador-bug>`
- **Refactorización de código**: `refactor/<ambito>`
- **Tareas de mantenimiento, CI o configuración**: `chore/<tarea-mantenimiento>`
- **Documentación**: `docs/<tema>`
- **Optimización de rendimiento**: `perf/<mejora>`

> ⚠️ **Regla de oro**: Nunca confirmes cambios directamente sobre la rama `main`. Trabaja siempre en una rama de tema y envía un Pull Request.

---

## 2. Convención de Commits Atómicos (Conventional Commits)

Los mensajes de confirmación deben seguir estrictamente el estándar de **Conventional Commits**:

### Estructura
```text
<tipo>(<ambito>): <descripcion concisa en modo imperativo>

[cuerpo opcional con justificacion tecnica y contexto]

[BREAKING CHANGE: descripcion de incompatibilidad si aplica]
```

### Tipos Permitidos
- `feat`: Nuevas capacidades o funcionalidades visibles.
- `fix`: Corrección de errores en producción o lógica.
- `refactor`: Cambios en la estructura interna del código sin alterar su comportamiento externo.
- `test`: Incorporación o mejora de pruebas automatizadas.
- `docs`: Modificaciones exclusivamente en documentación.
- `style`: Ajustes de formato, espaciado o linting sin cambios de lógica.
- `perf`: Mejoras de rendimiento o reducción de latencia.
- `build`: Cambios en el sistema de empaquetado o dependencias.
- `ci`: Modificaciones en pipelines de CI/CD (GitHub Actions, etc.).
- `chore`: Mantenimiento general, actualización de configuración o herramientas.

### Atomicidad
- Cada commit debe representar una unidad de cambio coherente e indivisible.
- No mezclar cambios de estilo/formato con lógica de negocio en el mismo commit.

---

## 3. Verificación y Calidad Local

Antes de enviar un Pull Request o solicitar revisión, ejecuta la suite de pruebas localmente:

```bash
# 1. Validación de sintaxis y compilación
python -m compileall src/

# 2. Prueba de concurrencia y DecisionManager
python test_decision_flow.py

# 3. Prueba interactiva de Textual TUI (opcional pero recomendada)
python test_ui_interactive.py
```

---

## 4. Política de Publicación Segura (Safe Publishing)

- **Protección de Secretos**: Nunca agregues archivos `.env` o credenciales de API al repositorio. Revisa siempre `git status -s` antes de confirmar.
- **Directorio de Salida**: Los archivos generados durante la ejecución de los agentes residen en `output/` y están ignorados por defecto en Git (excepto `output/.gitkeep`).
- **Resolución de Conflictos**: En caso de conflicto al rebasar o fusionar, no forces el historial con `push --force` en ramas compartidas. Consulta al equipo antes de alterar el historial público.
