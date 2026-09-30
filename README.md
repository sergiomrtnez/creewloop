# ⚡ CreewLoop :: Factoría de Software Interactiva

> Factoría autónoma de desarrollo de software basada en especificaciones (**SDD - Specification-Driven Development**) orquestada con **CrewAI** e interfaz de terminal interactiva (**Textual**). Soporta modelos locales (**Ollama**, **LM Studio**) y proveedores en la nube (**OpenAI**, **Anthropic**, **Gemini**).

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/Orchestrator-CrewAI-FF4B4B?style=flat)
![Textual](https://img.shields.io/badge/UI-Textual%20TUI-00D2FF?style=flat)
![LiteLLM](https://img.shields.io/badge/LLM%20Wrapper-LiteLLM-4E79A7?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

---

## 📑 Tabla de Contenidos
- [1. Visión General del Proyecto](#1-visión-general-del-proyecto)
- [2. Arquitectura Crítica de Concurrencia (Threading)](#2-arquitectura-crítica-de-concurrencia-threading)
- [3. Estructura del Proyecto y Archivos](#3-estructura-del-proyecto-y-archivos)
- [4. Diseño de la Interfaz (Textual TUI)](#4-diseño-de-la-interfaz-textual-tui)
- [5. Flujo de Agentes (Specification-Driven Development)](#5-flujo-de-agentes-specification-driven-development)
- [6. Herramientas Preparadas para Futuras Integraciones](#6-herramientas-preparadas-para-futuras-integraciones)
- [7. Instalación y Requisitos](#7-instalación-y-requisitos)
- [8. Batería de Pruebas Automatizadas](#8-batería-de-pruebas-automatizadas)
- [9. Guía de Uso y Modos de Ejecución](#9-guía-de-uso-y-modos-de-ejecución)
- [10. Atajos de Teclado (Keybindings)](#10-atajos-de-teclado-keybindings)

---

## 1. Visión General del Proyecto

**CreewLoop** transforma un prompt de alto nivel en software ejecutable y documentado mediante un equipo colaborativo de agentes inteligentes. El sistema sigue rigurosamente el paradigma **SDD (Specification-Driven Development)**:

1. **Especificación primero**: Se genera y valida iterativamente un Documento de Diseño de Software (**SDD**) en Markdown (`output/sdd.md`).
2. **Humano en el bucle (Human-in-the-Loop)**: Los agentes consultan al usuario antes de tomar decisiones técnicas críticas (alcance MVP, stack tecnológico, bases de datos, aprobación final).
3. **Código real y ejecutable**: El agente desarrollador genera código funcional en el sistema de archivos local (`output/`).
4. **Verificación y despliegue**: Los agentes de QA y DevOps preparan las pruebas y empaquetan la solución (Docker y Git).

---

## 2. Arquitectura Crítica de Concurrencia (Threading)

### El Reto Técnico
- **CrewAI** es **síncrono y bloqueante**: cuando un agente razona, invoca herramientas o ejecuta tareas, bloquea el hilo donde se ejecuta.
- **Textual** es **asíncrono (`asyncio`)**: opera sobre un bucle de eventos para renderizar la interfaz a 60 FPS y procesar eventos de ratón/teclado.
- *Problema*: Ejecutar CrewAI en el hilo de la UI congela completamente la pantalla.
- *Solución*: Aislar la ejecución de CrewAI en un **Worker de hilo secundario** (`@work(thread=True)`), coordinando las pausas de decisión mediante un gestor de estado basado en `threading.Event()`.

### Diagrama de Secuencia y Sincronización

```
┌──────────────────────────────────────┐          ┌──────────────────────────────────────┐
│  Hilo Secundario (Worker de CrewAI)  │          │   Hilo Principal (Textual / Async)   │
└──────────────────┬───────────────────┘          └──────────────────┬───────────────────┘
                   │                                                 │
      [Agente ejecuta tarea SDD]                                     │
                   │                                                 │
      [Agente invoca AskHumanTool]                                   │
                   │                                                 │
                   ├───── DecisionManager.ask(pregunta, opciones) ───┤
                   │                                                 │
         threading.Event.wait()                                      ▼
           [HILO EN PAUSA] ⏸                            app.call_from_thread(...)
                   │                                                 │
                   │                                   Renderiza DecisionBox en UI:
                   │                                   - Pregunta formateada
                   │                                   - Botones interactivos con opciones
                   │                                   - Input para respuesta manual
                   │                                                 │
                   │                                     [Usuario hace clic en opción]
                   │                                                 │
                   │                                   DecisionManager.resolve(respuesta)
                   │                                                 │
                   │                                       threading.Event.set()
                   │                                                 │
         [HILO SE REANUDA] ▶ ────────────────────────────────────────┘
                   │
      [Agente recibe la decisión del usuario]
                   │
      [Continúa siguiente paso del SDD]
```

### Componentes de Concurrencia
- **`DecisionManager` (`src/core/decision_manager.py`)**: Singleton thread-safe que gestiona `threading.Event()` y `threading.Lock()`. Mantiene el estado de espera, emite el callback a la UI y bloquea/desbloquea el worker.
- **`AskHumanDecisionTool` (`src/tools/human_decision_tool.py`)**: Herramienta de CrewAI que hereda de `BaseTool`. Expone parámetros estructurados (`question`, `options`) mediante Pydantic y pausa al agente hasta recibir respuesta humana.
- **`EventBus` (`src/core/event_bus.py`)**: Bus desacoplado que envía logs, cambios de estado y actualizaciones de archivos desde los hilos hacia los widgets de Textual de forma segura mediante `self.call_from_thread()`.

---

## 3. Estructura del Proyecto y Archivos

```
creewloop/
├── .venv/                              # Entorno virtual aislado (Python 3.11+)
├── output/                             # Directorio de trabajo donde se generan los artefactos
│   ├── sdd.md                          # Documento de Diseño de Software en tiempo real
│   ├── task_manager.py                 # Código fuente generado por los agentes
│   └── Dockerfile                      # Empaquetado generado por DevOps
├── requirements.txt                    # Dependencias del proyecto
├── .env.example                        # Plantilla de configuración de variables de entorno
├── README.md                           # Documentación técnica exhaustiva
├── run.py                              # Script de entrada para lanzar la aplicación
├── test_decision_flow.py               # Test unitario del gestor de decisiones con Event()
├── test_ui_interactive.py             # Test e2e de la UI simulando clics y resolución
└── src/
    ├── __init__.py
    ├── config.py                       # Configuración y fábrica de LLM (LiteLLM)
    ├── core/
    │   ├── __init__.py
    │   ├── decision_manager.py         # Núcleo de concurrencia y sincronización
    │   └── event_bus.py                # Publicador/Suscriptor thread-safe
    ├── tools/
    │   ├── __init__.py
    │   ├── human_decision_tool.py      # Tool de decisión interactiva (AskHumanDecisionTool)
    │   ├── docker_placeholder.py       # Tool de validación en Docker (Docker SDK)
    │   └── git_placeholder.py          # Tool de versionado y GitHub (GitPython / PyGithub)
    ├── agents/
    │   ├── __init__.py
    │   └── factory_crew.py             # Definición de los 6 agentes y tareas del SDD
    └── ui/
        ├── __init__.py
        ├── app.py                      # Clase principal Textual (CreewLoopApp)
        ├── styles.tcss                 # Estilos CSS de Textual (tema oscuro de alto contraste)
        └── components/
            ├── __init__.py
            ├── sidebar.py              # Barra lateral: configuración de proveedor, modelo y prompt
            ├── execution_panel.py      # Panel central: logs en vivo y DecisionBox con botones
            └── document_viewer.py      # Panel derecho: visor reactivo de SDD y visor de código
```

---

## 4. Diseño de la Interfaz (Textual TUI)

La interfaz se divide en **tres paneles funcionales principales** optimizados para claridad y ergonomía en terminal:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚡ CREEWLOOP FACTORY  :: SDD Orchestration Engine                      ● RUNNING CREW  │
├───────────────────┬──────────────────────────────────┬─────────────────────────────────┤
│ ⚙️ CONFIGURACIÓN   │ 💬 CHAT Y LOGS EN VIVO           │ 📄 VISOR REACTIVO (SDD / CODE)  │
│                   │                                  │                                 │
│ [Proveedor]       │ [INFO] Analizando alcance...     │ [Tab: 📋 SDD] [Tab: 💻 Código] │
│ Ollama / OpenAI   │ [INFO] Generando arquitectura... │                                 │
│                   │                                  │ # Software Design Document      │
│ [Nombre Modelo]   │ ┌──────────────────────────────┐ │ ## 1. Alcance del Proyecto      │
│ ollama/llama3.2   │ │ 🤖 Architect necesita tu     │ │ - Persistencia: SQLite          │
│                   │ │    decisión:                 │ │ - Arquitectura: Modular         │
│ [Clave API]       │ │ ❓ ¿Qué base de datos usar?  │ │                                 │
│ ••••••••••••      │ │                              │ ```python                         │
│                   │ │ [ SQLite ] [ PostgreSQL ]    │ class TaskRepository:             │
│ [Prompt Proyecto] │ │                              │     ...                           │
│ Construir API...  │ │ [Input texto manual...]      │ ```                               │
│                   │ └──────────────────────────────┘ │                                 │
│ [🚀 Launch]       │                                  │                                 │
│ [⚡ Demo] [⏹ Stop]│                                  │                                 │
└───────────────────┴──────────────────────────────────┴─────────────────────────────────┘
```

1. **Barra Lateral (Sidebar / Configuración)**:
   - Selector reactivo de proveedores: **Ollama**, **LM Studio**, **OpenAI**, **Anthropic**, **Gemini**.
   - Input de modelo preconfigurado según el proveedor seleccionado (ej. `ollama/llama3.2`, `openai/gpt-4o-mini`).
   - Inputs para clave de API (enmascarada) y URL base personalizada (ej. `http://localhost:11434` o `http://localhost:1234/v1`).
   - Área de texto para describir el proyecto a desarrollar.
   - Botones de acción: `Launch Factory`, `Test Decision Flow (Demo)` y `Stop`.

2. **Panel Central / Izquierdo (Ejecución y Decisiones)**:
   - Feed de logs estilizado con `RichLog` en tiempo real (clasificado por colores: `INFO`, `WARNING`, `SUCCESS`, `ERROR`).
   - Renderizado condicional del contenedor **`DecisionBox`** cuando un agente requiere intervención humana. Presenta botones accesibles con ratón o teclado para cada opción, además de un campo de texto libre para instrucciones personalizadas.

3. **Panel Derecho (Visor Reactivo de Documentación y Código)**:
   - Pestaña **📋 SDD Document**: Renderiza en tiempo real el archivo `sdd.md` conforme el Product Manager y el Arquitecto lo van ampliando.
   - Pestaña **💻 Generated Code**: Muestra los archivos de código fuente escritos por el Desarrollador Senior con sintaxis formateada.
   - Pestaña **📁 File Artifacts**: Lista los archivos generados en el directorio de salida con su tamaño en bytes.

---

## 5. Flujo de Agentes (Specification-Driven Development)

La factoría ejecuta un proceso secuencial estricto donde cada agente alimenta el trabajo del siguiente:

| Agente | Rol | Responsabilidad en el SDD | Interacción Humana (`AskHumanDecisionTool`) |
| :--- | :--- | :--- | :--- |
| 1. **Product Manager** | Senior Technical PM | Define alcance, casos de uso, personas y criterios de aceptación en `sdd.md`. | Valida el enfoque del MVP con el usuario. |
| 2. **Software Architect** | Principal Architect | Diseña el stack tecnológico, diagramas de componentes y patrones de diseño. | Presenta opciones de base de datos/frameworks para que el usuario decida. |
| 3. **UI/UX & Data Specialist** | UI/UX & Data Modeler | Modela esquemas relacionales/documentales y especificaciones de API. | Valida flujos de usuario y diseño de interfaces. |
| 4. **Senior Developer** | Senior Full-Stack Dev | Escribe código modular, tipado y funcional en la carpeta `output/`. | Consulta decisiones de implementación complejas. |
| 5. **QA Engineer** | Quality Assurance | Escribe tests unitarios y valida la ejecución en contenedor aislado. | Alerta sobre anomalías o casos límite. |
| 6. **DevOps Engineer** | Release Engineer | Genera `Dockerfile`, `README.md` y prepara el control de versiones en Git. | Solicita aprobación final para el empaquetado y release. |

---

## 6. Herramientas Preparadas para Futuras Integraciones

El sistema incluye herramientas modulares con la estructura base lista para conectar servicios externos:

- **`DockerValidationTool` (`src/tools/docker_placeholder.py`)**:
  - Preparado para el **Docker SDK for Python** (`docker`).
  - Detecta si el daemon de Docker está activo (`client.ping()`) y permite ejecutar contenedores aislados para compilaciones y suites de tests reproducibles.
- **`GitOpsTool` (`src/tools/git_placeholder.py`)**:
  - Preparado para **GitPython** y **PyGithub**.
  - Inicializa repositorios locales (`git.Repo.init`), realiza commits automáticos y permite publicar el repositorio en GitHub mediante token de acceso.

---

## 7. Instalación y Requisitos

### Requisitos Previos
- **Python 3.11** o superior instalado en el sistema.
- Acceso a un LLM (Ollama o LM Studio corriendo localmente, o una API Key de OpenAI, Anthropic o Gemini).

### Paso 1: Configurar el Entorno Virtual
Para evitar conflictos con librerías globales, el proyecto utiliza un entorno virtual `.venv`:

```powershell
# En Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Paso 2: Instalar Dependencias
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Paso 3: Configurar Variables de Entorno (Opcional)
Copia la plantilla y configura tus claves si utilizas proveedores cloud:
```powershell
cp .env.example .env
```

---

## 8. Batería de Pruebas Automatizadas

El proyecto incluye dos suites de pruebas para validar tanto el núcleo de concurrencia como la interfaz gráfica:

### Test 1: Concurrencia y Sincronización con `threading.Event()`
Verifica que un hilo secundario que invoca `AskHumanDecisionTool` entra efectivamente en estado de pausa, no consume CPU y se reanuda inmediatamente cuando la interfaz invoca `resolve()`:

```powershell
.venv\Scripts\python.exe test_decision_flow.py
```

*Salida esperada:*
```text
==================================================================
[TEST] DecisionManager & AskHumanDecisionTool Concurrency
==================================================================
  [Worker Thread] Agent started task...
  [Worker Thread] Agent invoking DecisionManager.ask()...
  [UI Simulation] Received prompt: 'Which backend framework should we use?'
  [UI Simulation] Rendered options: ['FastAPI', 'Django', 'Flask']
  [Main Thread] Confirmed: Agent worker thread is successfully PAUSED.
  [Main Thread] Simulating user thinking...
  [Main Thread] User clicks option button: 'FastAPI'
  [Worker Thread] Agent unblocked after 1.10s with answer: 'FastAPI'

[PASS] DecisionManager correctly pauses worker thread and resumes upon UI resolve()!
==================================================================
```

### Test 2: Prueba End-to-End de la Interfaz Textual
Utiliza el `App.run_test()` de Textual para montar la interfaz de forma headless, pulsar el botón de demostración, esperar a que el agente pause y monte el contenedor `DecisionBox`, simular el clic del usuario sobre un botón interactivo y confirmar que el worker se desbloquea:

```powershell
.venv\Scripts\python.exe test_ui_interactive.py
```

*Salida esperada:*
```text
==================================================================
[TEST] Full Interactive Textual UI & Decision Flow
==================================================================
  1. Textual App mounted.
  2. Triggering 'Test Decision Flow'...
  3. Waiting for agent to request decision in UI...
  4. Confirmed: Agent paused and DecisionBox mounted on screen!
  5. Found 4 option buttons in DecisionBox.
  6. Simulating human clicking button: 'CLI Application'...
  7. Confirmed: DecisionBox unmounted, worker unblocked and running!

[PASS] End-to-end Textual UI & DecisionManager flow verified successfully!
==================================================================
```

---

## 9. Guía de Uso y Modos de Ejecución

Inicia la factoría ejecutando:

```powershell
.venv\Scripts\python.exe run.py
```

### Modo 1: Demostración Interactiva (`⚡ Test Decision Flow (Demo)`)
- No requiere API keys ni conexión a internet.
- Simula el ciclo completo de agentes: el **Product Manager** y el **Arquitecto** formularán preguntas de diseño en la pantalla, montando botones de decisión interactivos.
- Al seleccionar una opción, el SDD (`output/sdd.md`), el código (`output/task_manager.py`) y el `Dockerfile` se generarán reactivamente en pantalla.

### Modo 2: Factoría Real con Agentes (`🚀 Launch Factory`)
1. Selecciona tu proveedor en la barra lateral:
   - **Ollama**: Asegúrate de tener Ollama corriendo (`ollama serve`). Modelo por defecto: `ollama/llama3.2`.
   - **LM Studio**: Inicia el servidor local en LM Studio (`http://localhost:1234/v1`).
   - **OpenAI / Anthropic / Gemini**: Introduce tu clave de API en el campo correspondiente.
2. Escribe los requisitos del software que deseas generar en el cuadro de texto.
3. Haz clic en **🚀 Launch Factory**.
4. Sigue la ejecución en el panel central y responde a las preguntas de los agentes haciendo clic en las opciones propuestas.

---

## 10. Atajos de Teclado (Keybindings)

| Atajo | Acción | Descripción |
| :---: | :--- | :--- |
| `Ctrl + Q` | **Salir** | Cierra la aplicación de forma segura y cancela los hilos activos. |
| `Ctrl + B` | **Alternar Barra Lateral** | Oculta o muestra la barra de configuración para mayor espacio visual. |
| `Ctrl + R` | **Recargar Archivos** | Actualiza manualmente la lista de artefactos y el visor de documentos. |
| `Tab` / `Shift+Tab` | **Navegación** | Mueve el foco entre los diferentes inputs, botones y paneles. |
