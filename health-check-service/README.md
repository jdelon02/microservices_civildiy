# Health Check Service

A dedicated microservice for aggregating and proxying health checks from all microservices in the system.

## Purpose

The Health Check Service provides a single, centralized point for querying the health status of all microservices. It:

1. **Proxies health requests** to individual services that are running on the internal Docker network
2. **Aggregates health data** from multiple services for system-wide status
3. **Handles cross-network requests** - can be queried from the frontend which runs in a browser
4. **Provides multiple endpoints** for different health check scenarios

## API Endpoints

### Service Health Endpoints

- `GET /health` - Liveness probe
- `GET /ready` - Readiness probe (checks Consul connectivity)

### Health Status Endpoints

- `GET /api/health/services` - Get health for all registered services
- `GET /api/health/service/{serviceName}` - Get health for a specific service
- `GET /api/health/service/{serviceName}/{endpoint}` - Get health for a specific service endpoint
- `GET /api/health/status` - Get overall system health with category breakdown

## Examples

```bash
# Get all services health
curl http://localhost:5000/api/health/services

# Get specific service health
curl http://localhost:5000/api/health/service/book-catalog-service

# Get specific endpoint health
curl http://localhost:5000/api/health/service/book-catalog-service/ready
curl http://localhost:5000/api/health/service/book-review-service/health/db

# Get system-wide health status
curl http://localhost:5000/api/health/status
```

## Architecture

- **Consul Integration**: Queries Consul to discover services and their addresses
- **Async/Await**: Uses asyncio for concurrent health checks
- **Error Handling**: Gracefully handles timeouts and service unavailability
- **Service Discovery**: Automatically discovers services registered with Consul

## Environment Variables

- `CONSUL_HOST` - Consul server host (default: consul-server)
- `CONSUL_PORT` - Consul server port (default: 8500)
- `SERVICE_HOST` - This service's host for Consul registration (default: health-check-service)
