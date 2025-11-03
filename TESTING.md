# Testing Microservices

## Prerequisites

1. Start all containers: `docker-compose up -d`
2. Verify all containers are running: `docker-compose ps`
3. Install `curl` (usually pre-installed on macOS)

## Service Testing Order

### 1. Infrastructure Health
```bash
# Consul UI
open http://localhost:8500

# Traefik Dashboard
open http://localhost:8080

# Redis
docker exec -it read-db redis-cli ping

# MongoDB
docker exec -it mongodb mongosh --eval "db.adminCommand('ping')"

# PostgreSQL
docker exec -it postgres-db psql -U user -d microservices_db -c "SELECT 1"
```

### 2. Auth Service

**Register User:**
```bash
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "securepassword123"
  }'
```

**Login & Get Token:**
```bash
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
# Response includes: access_token, token_type, expires_in
```

**Health Check:**
```bash
curl http://localhost/api/auth/health
```

### 3. User Profile Service

**Create Profile (requires valid JWT):**
```bash
TOKEN="<access_token_from_login>"

curl -X POST http://localhost/api/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "dob": "1990-01-15",
    "address": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip_code": "10001",
    "country": "USA",
    "phone": "555-1234",
    "bio": "Software engineer",
    "preferences": "{\"theme\": \"dark\"}"
  }'
```

**Get Profile:**
```bash
curl http://localhost/api/profile \
  -H "Authorization: Bearer $TOKEN"
```

**Update Profile:**
```bash
curl -X PUT http://localhost/api/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "city": "San Francisco",
    "state": "CA"
  }'
```

**Delete Profile:**
```bash
curl -X DELETE http://localhost/api/profile \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Posts Service

**Create Post (requires valid JWT):**
```bash
TOKEN="<access_token_from_login>"

curl -X POST http://localhost/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Post",
    "content": "This is the content of my post",
    "tags": ["introduction", "hello"]
  }'
# Response includes: id, user_id, title, content, tags, created_at, updated_at
```

**Get Post:**
```bash
POST_ID="<id_from_create_response>"

curl http://localhost/api/posts/$POST_ID
```

**List Posts:**
```bash
# All posts
curl http://localhost/api/posts

# Filter by user
curl http://localhost/api/posts?user_id=1

# Pagination
curl http://localhost/api/posts?limit=5&skip=0
```

**Update Post (owner only):**
```bash
curl -X PUT http://localhost/api/posts/$POST_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "content": "Updated content"
  }'
```

**Delete Post (owner only):**
```bash
curl -X DELETE http://localhost/api/posts/$POST_ID \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Feed Generator Service

**Check Feed Stats:**
```bash
curl http://localhost/api/activity-stream/stats
```

**Get Global Activity Stream:**
```bash
# Latest 20 items
curl http://localhost/api/activity-stream

# Pagination
curl http://localhost/api/activity-stream?limit=5&skip=0
```

**Get User Activity Stream (requires JWT):**
```bash
TOKEN="<access_token_from_login>"

curl http://localhost/api/activity-stream/user \
  -H "Authorization: Bearer $TOKEN"
```

## End-to-End Testing Flow

1. Register a user
2. Login to get JWT token
3. Create a user profile
4. Create 3-5 posts
5. Wait 2-3 seconds for Kafka events to propagate
6. Check global activity stream
7. Check user-specific activity stream
8. Verify posts are sorted by timestamp (newest first)

## Debugging

**Check service logs:**
```bash
docker logs auth-service
docker logs user-profile-service
docker logs posts-service
docker logs feed-generator-service
```

**Monitor Kafka messages:**
```bash
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server kafka:9092 \
  --topic posts-events \
  --from-beginning
```

**Check Redis data:**
```bash
docker exec -it read-db redis-cli
> LRANGE feed:activity:global 0 -1
> LRANGE feed:activity:user:1 0 -1
```

**Check MongoDB data:**
```bash
docker exec -it mongodb mongosh
> use posts_db
> db.posts.find()
```

## Common Issues

**JWT Token Invalid:**
- Make sure you're using the `access_token` from login response
- Token expires after 24 hours

**Cannot access /api/profile without JWT:**
- Profile endpoints require JWT validation via Traefik
- Make sure to include `Authorization: Bearer <token>` header

**Posts not appearing in feed:**
- Check that Kafka consumer is running: `docker logs feed-generator-service`
- Verify events are being published: `docker logs posts-service`
- Wait a few seconds for events to propagate

**MongoDB connection errors:**
- Ensure MongoDB is running: `docker-compose ps`
- Check connection string in posts-service env vars
