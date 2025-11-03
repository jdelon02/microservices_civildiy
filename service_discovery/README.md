# Service Discovery Mechanism (Service Registry)

This component acts as the "phonebook" of the microservices ecosystem. It stores the location and health status of all running microservices, allowing the API Gateway (and other services) to dynamically find where to route traffic.

## Technology Stack

*   **Primary Tool:** HashiCorp Consul (Open Source Version)

## Key Features

*   **Service Registration:** Receives announcements from all services, including the `auth-service`, `posts-service`, and the new components:
    *   `kafka-service` (the event broker)
    *   `read-db-service` (the Redis/PostgreSQL read database)
    *   `feed-generator-service` (the read model)
*   **Health Checking:** Periodically checks the health endpoints (`/health`) of registered services.
*   **HTTP/DNS API:** Provides APIs for the API Gateway and microservices to query service locations dynamically.
*   **Fault Tolerance:** Designed to be highly available and resilient to node failures.

## Getting Started (using Consul)

1.  **Docker Image:** `hashicorp/consul:latest` (or a specific version)
2.  **Basic Usage in `docker-compose.yml`:**
    ```yaml
    version: '3.8'
    services:
      consul-server:
        image: hashicorp/consul:latest
        command: agent -server -ui -node=server-1 -bootstrap-expect=1 -client=0.0.0.0
        ports:
          - "8500:8500" # Consul UI and API port
          - "8600:8600/tcp" # Consul DNS port (TCP)
          - "8600:8600/udp" # Consul DNS port (UDP)
    ```
3.  **Basic Usage Instructions:**
    *   The Consul UI at `http://localhost:8500` will now show the `auth-service`, `posts-service`, `videos-service`, `feed-generator-service`, and the infrastructure services like Kafka and the read database.
    *   All microservices make API calls to the Consul agent's API to announce themselves.
