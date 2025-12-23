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

