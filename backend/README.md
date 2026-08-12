# ClaimIQ - FastAPI Application

A FastAPI application for file processing and AI-powered querying with MongoDB, Redis/Valkey, Qdrant, and a LiteLLM gateway.

## Features

- File upload and processing
- AI-powered document querying through LiteLLM's OpenAI-compatible API
- Asynchronous task processing with RQ
- MongoDB for data persistence
- Redis/Valkey for queue management

## Prerequisites

- Docker and Docker Compose
- Provider API keys configured for the LiteLLM gateway

## Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd claimIQ
```

2. Copy the environment file and configure:
```bash
cp .env.example .env
# Edit .env with your actual values
```

3. Start the development environment:
```bash
docker-compose up --build
```

The application will be available at:
- API: http://localhost:8000
- LiteLLM Proxy: http://localhost:4000
- MongoDB: localhost:27017
- Valkey/Redis: localhost:6379

## Production Deployment

1. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with production values
```

2. For SSL/HTTPS, place your certificates in the `ssl/` directory:
```bash
mkdir ssl
# Copy your cert.pem and key.pem files to ssl/
```

3. Update nginx.conf to uncomment SSL configuration lines

4. Deploy with production compose file:
```bash
docker-compose -f docker-compose.prod.yml up --build -d
```

## API Endpoints

- `GET /` - Health check
- `POST /upload` - Upload a file for processing
- `POST /query` - Query processed documents

## Services

### Application (app)
- FastAPI web server
- Handles file uploads and queries
- Port: 8000

### LiteLLM (litellm)
- OpenAI-compatible gateway for chat and embedding requests
- Stores provider credentials at the gateway boundary
- Port: 4000 in development

### MongoDB (mongo)
- Document database
- Stores file metadata and processing status
- Port: 27017

### Valkey/Redis (valkey)
- Queue backend for RQ
- Port: 6379

### Worker (worker)
- Background task processor
- Processes uploaded files

### Nginx (production only)
- Reverse proxy and load balancer
- SSL termination
- Rate limiting
- Ports: 80, 443

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Gemini key used by LiteLLM | Optional, depending on configured models |
| `OPENAI_API_KEY` | OpenAI key used by LiteLLM | Optional, depending on configured models |
| `LITELLM_API_KEY` | Key used by ClaimIQ to call the proxy; use the master key unless virtual keys are configured | Required |
| `LITELLM_MASTER_KEY` | Key used by the LiteLLM proxy | Required |
| `LITELLM_BASE_URL` | Internal proxy URL | `http://litellm:4000` |
| `VECTOR_EMBEDDING_PROVIDER` | Embedding alias selection | `openai` |
| `VECTOR_DIMENSIONS` | Existing Qdrant vector dimension | `1536` |
| `MONGO_ROOT_USERNAME` | MongoDB root username | admin |
| `MONGO_ROOT_PASSWORD` | MongoDB root password | admin |
| `PYTHONPATH` | Python path | /app |
| `PYTHONUNBUFFERED` | Python unbuffered output | 1 |

## File Storage

Uploaded files are stored in the `/mnt/uploads` directory within the container, which is mounted as a Docker volume for persistence.

## Monitoring and Logs

View logs for all services:
```bash
docker-compose logs -f
```

View logs for a specific service:
```bash
docker-compose logs -f app
docker-compose logs -f worker
docker-compose logs -f mongo
docker-compose logs -f valkey
```

## Scaling

To scale the worker processes:
```bash
docker-compose up --scale worker=3
```

## Troubleshooting

1. **Connection refused errors**: Ensure all services are running and healthy
2. **File upload issues**: Check volume mounts and permissions
3. **Queue not processing**: Verify Valkey/Redis connection and worker status
4. **Database connection issues**: Check MongoDB credentials and network connectivity

## Development

For development with hot reload, the docker-compose.yml includes volume mounts for the application code. Changes to Python files will be reflected without rebuilding the container.

To rebuild after dependency changes:
```bash
docker-compose down
docker-compose up --build
