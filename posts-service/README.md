# Posts Microservice (Write Model)

This service manages all CRUD operations related to user posts. It now operates as the "Write Model" in our CQRS architecture, meaning it focuses solely on database writes and event emission.

## Technology Stack

*   **Framework:** FastAPI/Flask
*   **Database:** PostgreSQL (primary data storage)
*   **Event Library:** `confluent-kafka` (for producing events)
*   **Libraries:** `fastapi`, `sqlalchemy`, `psycopg2`, `confluent-kafka`

## Key Features

*   **CRUD Operations:** Handles creating, reading, updating, and deleting posts (`/posts` endpoints).
*   **Event Emission:** After a post is successfully created in the database, it publishes a `PostCreated` event to Kafka.
*   **`GET /health`:** Health check endpoint for Consul.

## Getting Started

1.  **Docker Image:** Based on a standard Python image (`python:3.11-slim`).
2.  **Modifications:**
    *   Add `confluent-kafka` to `requirements.txt`.
    *   Modify the post creation logic in your code to include a step that produces a message to a Kafka topic after a successful database transaction.
    *   Ensure the service registers itself with Consul upon startup.