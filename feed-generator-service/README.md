# Feed Generator Microservice (Read Model)

This service implements the "Read Side" of the CQRS pattern. Its primary function is to consume events from the event stream (Kafka/RabbitMQ) and maintain a fast, denormalized **materialized view** of all recent activity across posts and videos.

## Technology Stack

*   **Framework:** FastAPI
*   **Event Library:** `confluent-kafka` (for consuming events)
*   **Database:** Redis (recommended for fast in-memory lookups of time-sorted feeds) or PostgreSQL
*   **Libraries:** `fastapi`, `uvicorn`, `confluent-kafka`, `redis-py`

## Key Features

*   **Event Consumer:** Subscribes to "Post Created" and "Video Uploaded" events.
*   **Materialized View Maintenance:** Updates the Redis database with new activity items as events arrive.
*   **`GET /api/activity-stream`:** Exposes a very fast, read-only endpoint to serve the pre-generated, time-sorted feed to the API Gateway.
*   **`GET /health`:** Health check endpoint for the service registry (Consul).

## Getting Started

1.  **Docker Image:** Based on a standard Python image (e.g., `python:3.11-slim`).
2.  **Basic `Dockerfile`:**
    ```dockerfile
    FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY . .
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
    ```
3.  **Basic Usage Instructions:**
    *   Implement a background task in FastAPI to run the Kafka consumer logic continuously.
    *   Ensure the consumer logic parses events, extracts relevant data, and inserts/updates the Redis or PostgreSQL database.
    *   The `GET /api/activity-stream` route simply retrieves the data from the local database.
