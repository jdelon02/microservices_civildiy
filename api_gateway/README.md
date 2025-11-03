# API Gateway

The API Gateway is the single entry point for all external client requests. It is responsible for routing traffic to the correct internal microservices, authenticating users, applying rate limits, and load balancing requests.

## Technology Stack

*   **Primary Tool:** Traefik (a modern HTTP reverse proxy and load balancer that integrates with Docker labels).
*   **Alternative:** NGINX Open Source (requires `consul-template` for dynamic configuration updates).

## Key Features

*   **Dynamic Routing:** Discovers services automatically using Docker labels or a service registry (Consul/etcd).
*   **Authentication:** Validates JWTs provided by the client.
*   **Load Balancing:** Distributes requests among healthy service instances.

## Getting Started (using Traefik)

1.  **Docker Image:** `traefik:v2.10` (or a recent v2+ version)
2.  **Basic Usage in `docker-compose.yml`:**
    ```yaml
    version: '3.8'
    services:
      api-gateway:
        image: traefik:v2.10
        command:
          - "--api.insecure=true" # Enables the dashboard for local dev
          - "--providers.docker=true"
          - "--providers.docker.exposedbydefault=false" # Only expose services with specific labels
          - "--entrypoints.web.address=:80"
        ports:
          - "80:80"
          - "8080:8080" # The Traefik dashboard port
        volumes:
          - "/var/run/docker.sock:/var/run/docker.sock:ro" # Required to monitor Docker events
      # Other services go below, with traefik labels
    ```
3.  **Basic Usage Instructions:**
    *   **Define Routes with Labels:** Attach labels to your microservices in the `docker-compose.yml` file to tell Traefik how to route traffic to them.
    *   **Example for an 'Auth' service:**
      ```yaml
        auth-service:
          # ... image and other config ...
          labels:
            - "traefik.enable=true"
            - "traefik.http.routers.auth.rule=Host(`localhost`) && PathPrefix(`/api/auth`)"
            - "traefik.http.routers.auth.entrypoint=web"
      ```

---