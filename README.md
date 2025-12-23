# Fullstack ReactJS + Python + Integraciones + RPA

## Quickstart

### Opción 1: Con Docker Compose

```bash
# 1. Clonar y configurar
> git clone git@github.com:161tochtli/lglr.git
> cd lglr
> cp backend/.env.example backend/.env

# 2. Levantar todo el stack
> docker compose -f infra/docker-compose.yml up --build

# 3. Abrir http://localhost:5173
```
>
> Levanta: Frontend + API + Worker + PostgreSQL + Redis.
> 
> Si cambias `backend/.env` después de levantar, reinicia con: `docker compose -f infra/docker-compose.yml down && docker compose -f infra/docker-compose.yml up`

### Opción 2: Con Dev Containers en VS Code

```bash
# 1. Clonar
> git clone git@github.com:161tochtli/lglr.git
> cd lglr

# 2. Copiar el archivo backend/.env.example a backend/.env para configurar variables de entorno (p. ej. para usar OpenAI API) 
> cp backend/.env.example backend/.env

# 3. Abrir en VS Code
# Si aparece el popup: 
#   - Click "Reopen in Container"
# Si no aparece el popup:
#   - Instalar extensión "Dev Containers" (ms-vscode-remote.remote-containers)
#   - Ctrl+Shift+P → "Dev Containers: Reopen in Container"

# 4. Dentro del container:
> cd backend && uvicorn app.main:app --reload --port 8000

# 5. Frontend (otra terminal en el container):
> cd frontend && npm install
> npm run dev                     # Puerto default: 5173
# > npm run dev -- --port 5173    # Para usar otro puerto

# 6. Abrir http://localhost:5173
```


> 
> Si cambias `backend/.env` después de crear el container, reconstruye con: `Ctrl+Shift+P → "Dev Containers: Rebuild Container"`

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                               │
│                         http://localhost:5173                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Transactions  │     RPA (Wikipedia)     │     Summarize (OpenAI)           │
│  - Listar      │     - Buscar término    │     - Enviar texto               │
│  - Crear       │     - Extraer párrafo   │     - Obtener resumen            │
│  - Procesar    │     - Resumir con AI    │                                  │
└────────┬───────┴────────────┬────────────┴──────────────┬───────────────────┘
         │                    │                           │
         ▼                    ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                 │
│                        http://localhost:8000                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  /api/transactions/*  │  /api/rpa/*  │  /api/assistant/*  │  /ws/*          │
├───────────────────────┴──────────────┴────────────────────┴─────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │   Domain    │    │   Services  │    │    Repos    │    │    Infra    │   │
│  │  - Models   │    │ - Summarize │    │ - InMemory  │    │ - Queue     │   │
│  │  - Events   │    │             │    │ - SQLite    │    │ - OpenAI    │   │
│  │             │    │             │    │ - Postgres  │    │ - Events    │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
         │                           │                           │
         ▼                           ▼                           ▼
   ┌───────────┐               ┌───────────┐             ┌───────────────┐
   │ PostgreSQL│               │   Redis   │             │    OpenAI     │
   │  :5432    │               │   :6379   │             │    API        │
   └───────────┘               └───────────┘             └───────────────┘
```

---

## Módulos del Backend

### 📁 `app/api/` - Endpoints REST

| Archivo | Endpoint | Descripción |
|---------|----------|-------------|
| `transactions.py` | `POST /transactions/create` | Crear transacción (idempotente) |
| | `POST /transactions/async-process` | Procesar transacción async |
| | `PATCH /transactions/{id}/status` | Cambiar estado de transacción |
| | `GET /transactions` | Listar transacciones |
| `summaries.py` | `POST /assistant/summarize` | Resumir texto con OpenAI |
| `rpa.py` | `POST /rpa/wikipedia-summarize` | Bot: Wikipedia → Resumen |
| `logs.py` | `GET /logs` | Obtener logs de eventos |
| | `GET /logs/grouped` | Logs agrupados por correlation_id |
| | `GET /logs/transaction/{id}` | Logs de una transacción específica |
| | `GET /logs/request/{id}` | Logs de un request específico |
| `websocket.py` | `WS /ws/transactions/stream` | Actualizaciones en tiempo real |
| `main.py` | `GET /health` | Health check endpoint |

### 📁 `app/domain/` - Lógica de Negocio

| Archivo | Contenido |
|---------|-----------|
| `models.py` | `Transaction`, `Summary`, `TransactionStatus`, `TransactionType` |
| `events.py` | Eventos de dominio: `transaction_created`, `status_changed`, etc. |
| `correlation.py` | Gestión de correlation IDs para trazabilidad |

### 📁 `app/repos/` - Repositorios (Persistencia)

| Archivo | Implementación |
|---------|----------------|
| `ports.py` | Interfaces/Protocols (`TransactionRepo`, `SummaryRepo`) |
| `in_memory.py` | Repositorios en memoria (testing) |
| `sqlite.py` | Persistencia SQLite |
| `postgres.py` | Persistencia PostgreSQL (producción) |

### 📁 `app/infra/` - Infraestructura

| Archivo | Función |
|---------|---------|
| `queue.py` | `InMemoryQueue`, `RedisQueue` - Colas de mensajes |
| `openai_client.py` | `OpenAIClientStub`, `OpenAIClientReal` - Cliente OpenAI |
| `events.py` | `EventBus` - Publicación/suscripción de eventos |
| `logging.py` | Configuración de structlog |
| `db.py` | Conexiones SQLite |
| `postgres.py` | Conexiones PostgreSQL |

### 📁 `app/rpa/` - Automatización

| Archivo | Función |
|---------|---------|
| `wikipedia_bot.py` | Bot httpx: busca en Wikipedia y extrae contenido |
| `extractor.py` | Parser HTML para extraer párrafos de Wikipedia |

### 📁 `app/worker/` - Procesamiento Async

| Archivo | Función |
|---------|---------|
| `handler.py` | Procesa jobs de la cola, actualiza estados de transacciones |

### 📁 `app/services/` - Servicios de Aplicación

| Archivo | Función |
|---------|---------|
| `summarize.py` | Orquesta: OpenAI client → Persistencia → Eventos |

---

## API Docs (Swagger/OpenAPI)

Una vez corriendo el backend:

| Recurso | URL |
|---------|-----|
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |
| **OpenAPI JSON** | http://localhost:8000/openapi.json |

---

## Testing

```bash
cd backend

# ─────────────────────────────────────────────────────────────
# Tests Unitarios (rápidos, sin I/O externo)
# ─────────────────────────────────────────────────────────────
pytest tests/unit/ -v

# ─────────────────────────────────────────────────────────────
# Tests de Integración
# ─────────────────────────────────────────────────────────────
pytest tests/integration/ -v             # Endpoints, persistencia, workers

# Con Redis (requiere Docker corriendo)
pytest tests/integration/test_redis_queue.py -v

# Con PostgreSQL (requiere DATABASE_URL)
pytest tests/integration/persistence/test_postgres.py -v

# ─────────────────────────────────────────────────────────────
# Tests E2E (lentos, requieren conexión a internet)
# ─────────────────────────────────────────────────────────────
pytest tests/e2e/ -v                     # Todos los tests e2e (httpx)

# ─────────────────────────────────────────────────────────────
# Comandos Útiles
# ─────────────────────────────────────────────────────────────
pytest                                   # Todos los tests
pytest -m "not slow"                     # Excluir tests lentos
pytest -m "not postgres"                 # Excluir tests que requieren PostgreSQL
pytest --cov=app --cov-report=html       # Con coverage report
```

### Estructura de Tests

```
tests/
├── unit/                    # Tests rápidos sin I/O
│   ├── test_domain.py       # Modelos y eventos
│   ├── test_services.py     # Servicios (OpenAI stub)
│   ├── test_queue.py        # Cola en memoria
│   └── ...
├── integration/             # Tests con I/O real
│   ├── api/                 # Endpoints HTTP
│   ├── persistence/         # SQLite, PostgreSQL
│   └── test_redis_queue.py  # Redis (Docker)
└── e2e/                     # Tests end-to-end
    └── test_rpa_wikipedia.py
```

## Frontend

### Secciones

| Tab | Función |
|-----|---------|
| **Transactions** | CRUD de transacciones con WebSocket para actualizaciones en tiempo real |
| **RPA** | Bot que busca en Wikipedia, extrae el primer párrafo y lo resume con OpenAI |
| **Summarize** | Envía texto directamente a OpenAI para obtener un resumen |

### Tecnologías

- **React 18** + TypeScript
- **Vite** para build/dev
- **WebSocket** para actualizaciones en tiempo real

---

## Estructura del Proyecto

```
legalario-prueba-tecnica/
├── backend/
│   ├── app/
│   │   ├── api/           # Endpoints REST + WebSocket
│   │   ├── domain/        # Modelos y eventos de dominio
│   │   ├── infra/         # Queue, OpenAI, DB connections
│   │   ├── repos/         # Repositorios (InMemory, SQLite, Postgres)
│   │   ├── rpa/           # Bot de Wikipedia
│   │   ├── services/      # Servicios de aplicación
│   │   ├── worker/        # Procesador de cola async
│   │   ├── main.py        # Entry point FastAPI
│   │   └── settings.py    # Configuración pydantic-settings
│   ├── tests/             # Tests unitarios e integración
│   ├── pyproject.toml     # Dependencias Python
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks (useWebSocket, useTransactions)
│   │   ├── styles/        # CSS
│   │   └── api.ts         # Cliente API
│   ├── package.json
│   └── Dockerfile
└── infra/
    └── docker-compose.yml # Stack completo

```

---

## Licencia
Proyecto Privado
