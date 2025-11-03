# User Authentication Microservice

This microservice is responsible for managing user credentials, handling the login process, and issuing/validating JSON Web Tokens (JWTs). It should focus solely on authentication logic.

## Technology Stack

*   **Framework:** FastAPI
*   **ASGI Server:** Uvicorn
*   **Key Python Libraries:**
    *   `fastapi`, `uvicorn`
    *   `passlib` (for password hashing, e.g., `bcrypt`)
    *   `PyJWT` (for creating and decoding tokens)
    *   `python-jose` (another robust JWT library)
    *   `httpx` (for self-registration to the service registry)

## Key Features

*   **`POST /api/auth/login`:** Validates user credentials and returns a JWT.
*   **`POST /api/auth/register`:** Creates a new user account.
*   **`GET /health`:** Endpoint for the service registry to perform health checks.
*   **Self-Registration:** Code executed on startup to announce its presence to the service registry (Consul/etcd).

## Getting Started

1.  **Docker Image:** Based on a standard Python image (e.g., `python:3.11-slim`).
2.  **Basic `Dockerfile`:**
    ```dockerfile
    FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY . .
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
    ```
3.  **Basic Usage Instructions:**
    *   Implement the FastAPI logic for hashing passwords and generating JWTs.
    *   Ensure the startup logic includes an `httpx.put` request to the Consul API to register the service dynamically.
    *   The service should listen on port `5000` (or another specified port) inside the container.