# Registro de Cambios (Changelog)

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning (SemVer)](https://semver.org/lang/es/).

## [Unreleased]

## [0.1.0] - 2026-09-30

### Añadido
- **Factoría de Software Interactiva con CrewAI**:
  - Orquestación SDD (*Specification-Driven Development*) con roles especializados (Product Manager, Solution Architect, Data Engineer, Senior Developer, QA Engineer, DevOps Specialist).
  - Documento de diseño iterativo `sdd.md` generado colaborativamente.
- **Núcleo de Concurrencia y Sincronización**:
  - `DecisionManager` basado en `threading.Event()` para pausar la ejecución de CrewAI en segundo plano sin congelar la interfaz.
  - `AskHumanDecisionTool` para consultas críticas humano-en-el-bucle (*Human-in-the-loop*).
  - `EventBus` reactivo para transmisión de logs y métricas de agentes.
- **Interfaz Gráfica de Terminal (Textual TUI)**:
  - Panel de ejecución con logs codificados por color y estado dinámico.
  - Componente `DecisionBox` interactivo montado en pantalla cuando un agente solicita aprobación humana.
  - Visor de artefactos (`sdd.md`, código fuente, Dockerfile) con pestañas y actualización reactiva.
  - Barra lateral de configuración y atajos de teclado completos (`Ctrl+D`, `Ctrl+X`, `Ctrl+R`, etc.).
- **Infraestructura de Versiones y Gobernanza GitHub**:
  - Configuración exhaustiva de `.gitignore` para Python, entornos virtuales y artefactos generados.
  - Pipeline de Integración Continua con GitHub Actions (`.github/workflows/ci.yml`).
  - Plantillas de Pull Request e Issues para GitHub (`.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/`).
  - Guía de contribución con trazabilidad Git y *Conventional Commits* (`CONTRIBUTING.md`).
  - Licencia de código abierto MIT (`LICENSE`).
