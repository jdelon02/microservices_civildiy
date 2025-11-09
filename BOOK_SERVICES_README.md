# Book Catalog and Review Microservices

This document describes the architecture and implementation of the Book Catalog Service and Book Review Service for the CivilDIY microservices platform.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│           Frontend (React)               │
├─────────────────────────────────────────┤
│         API Gateway (Traefik)           │
├─────────────────────────────────────────┤
│                                          │
├─→ /api/authors/*  ──→ Book Catalog      │
├─→ /api/books/*    ──→ Service           │
│                    (PostgreSQL)         │
│                                          │
├─→ /api/reviews/*  ──→ Book Review       │
├─→ /api/books/{id}/reviews ──→ Service   │
│                    (MongoDB + Redis)    │
│                                          │
├─→ (all) ──→ Feed Generator (consumes)   │
│             ├─ posts-events             │
│             └─ reviews-events (NEW)     │
│                                          │
└─────────────────────────────────────────┘
```

## Service 1: Book Catalog Service

### Purpose
Manages the canonical catalog of books and authors. Provides autocomplete for author searches and book lookups.

### Technology Stack
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (same as Auth & Profile services)
- **Architecture**: Relational database (Author → Book foreign key)

### Database Schema

```sql
-- Authors table
CREATE TABLE authors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    bio TEXT,
    created_by INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_author_name ON authors(name);

-- Books table
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author_id INT NOT NULL REFERENCES authors(id),
    isbn VARCHAR(20) UNIQUE,
    genre VARCHAR(100),
    description TEXT,
    cover_image_url VARCHAR(500),
    publication_year INT,
    created_by INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_author_id ON books(author_id);
CREATE INDEX idx_genre ON books(genre);
```

### Key Endpoints

#### Authors
```
POST   /api/authors                 # Create author
GET    /api/authors/search?q=name   # Autocomplete search (returns <= 10 authors)
GET    /api/authors/{id}            # Get author details
GET    /api/authors                 # List all authors (paginated)
```

#### Books
```
POST   /api/books                   # Create book
GET    /api/books/search?q=title&author_id=N&genre=sci-fi  # Search books
GET    /api/books/{id}              # Get book with author details
GET    /api/authors/{id}/books      # List books by author
GET    /api/books                   # List all books (paginated)
PUT    /api/books/{id}              # Update book
DELETE /api/books/{id}              # Delete book
```

### Response Models

```python
# Author
{
    "id": 1,
    "name": "Frank Herbert",
    "bio": "American science fiction novelist...",
    "created_at": "2025-01-01T00:00:00Z"
}

# Book (with author embedded)
{
    "id": 42,
    "title": "Dune",
    "author": {
        "id": 1,
        "name": "Frank Herbert",
        "bio": "...",
        "created_at": "..."
    },
    "isbn": "978-0441172719",
    "genre": "science fiction",
    "description": "Epic sci-fi novel...",
    "cover_image_url": "https://...",
    "publication_year": 1965,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
}
```

## Service 2: Book Review Service

### Purpose
Manages user book reviews with ratings, content, and helpfulness votes. Implements Redis caching for uniqueness checks (hybrid approach).

### Technology Stack
- **Framework**: FastAPI (Python)
- **Write Database**: MongoDB (reviews collection)
- **Cache Database**: Redis (uniqueness checks, positive/negative caching)
- **Event Stream**: Kafka (reviews-events topic)

### Uniqueness Strategy: Redis Cache + MongoDB Unique Index

**Problem**: Prevent users from creating duplicate reviews for the same book.

**Solution (Hybrid Approach)**:
1. **Redis Cache Layer** (fast, probabilistic)
   - Check: `user:{user_id}:book:{book_id}:review` → review_id (positive cache, 1 hour TTL)
   - Check: `user:{user_id}:book:{book_id}:no_review` → "1" (negative cache, 5 min TTL)
   - Falls back to database if cache miss
   
2. **MongoDB Unique Index** (ultimate safety net)
   - `UNIQUE(book_id, user_id)` constraint ensures no duplicates even with race conditions
   - Handles concurrent requests that both pass cache check
   - On duplicate: catch PyMongoError and return 409 Conflict

3. **Cache Invalidation**
   - Create review → Cache positive result (1 hour)
   - Delete review → Invalidate both caches
   - Update review → Keep cache valid (user still has reviewed)

### Database Schema

```javascript
// MongoDB: reviews collection
{
    "_id": ObjectId("..."),
    "book_id": 42,                          // Foreign key to Book Catalog Service
    "user_id": 123,                         // Foreign key to User Service
    "rating": 5,                            // 1-5 stars
    "content": "This was an amazing book!", // User's review text
    "tags": ["sci-fi", "thought-provoking"], // Review-specific tags
    "spoiler_warning": false,               // Metadata
    "helpful_count": 47,                    // Aggregate helpful votes
    "created_at": ISODate("2025-01-01T..."),
    "updated_at": ISODate("2025-01-01T...")
}

// Indexes
db.reviews.createIndex({ "book_id": 1 });
db.reviews.createIndex({ "user_id": 1 });
db.reviews.createIndex({ "created_at": -1 });
db.reviews.createIndex({ "book_id": 1, "user_id": 1 }, { "unique": true });
```

### Key Endpoints

#### Reviews CRUD
```
POST   /api/reviews                           # Create review (with uniqueness check)
GET    /api/reviews/{review_id}               # Get review
PUT    /api/reviews/{review_id}               # Update review (ownership verified)
DELETE /api/reviews/{review_id}               # Delete review (ownership verified)
```

#### Book Reviews
```
GET    /api/books/{book_id}/reviews?sort=recent&limit=10  # All reviews for book
GET    /api/books/{book_id}/rating            # Aggregate rating & count
POST   /api/reviews/{review_id}/mark-helpful  # Increment helpful count
```

#### User's Review
```
GET    /api/users/{user_id}/review-of/{book_id}  # Get user's review for book (or 404)
```

### Response Models

```python
# Review
{
    "id": "507f1f77bcf86cd799439011",
    "book_id": 42,
    "user_id": 123,
    "rating": 5,
    "content": "Amazing book!",
    "tags": ["sci-fi", "thought-provoking"],
    "spoiler_warning": false,
    "helpful_count": 47,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
}

# Book Rating
{
    "book_id": 42,
    "average_rating": 4.67,
    "review_count": 3
}
```

### Cache Behavior

#### Scenario 1: User Reviews Book for First Time
```
1. Request: POST /api/reviews { book_id: 42, rating: 5, ... }
2. Redis: Check cache for user:123:book:42:review → MISS
3. MongoDB: Query unique index → NOT FOUND
4. MongoDB: Insert review → SUCCESS
5. Redis: SET user:123:book:42:review = "review_id_999" EX 3600
6. Response: 201 Created with review details
```

#### Scenario 2: User Tries to Review Same Book Again
```
1. Request: POST /api/reviews { book_id: 42, rating: 3, ... }
2. Redis: Check cache for user:123:book:42:review → HIT "review_id_999"
3. Response: 409 Conflict (cached result, microseconds)
```

#### Scenario 3: User Updates Review
```
1. Request: PUT /api/reviews/review_id_999 { rating: 4, ... }
2. Verify ownership (from JWT)
3. MongoDB: Update review
4. Response: 200 OK (cache still valid - user still has reviewed)
5. Redis: No cache change needed
```

#### Scenario 4: User Deletes Review
```
1. Request: DELETE /api/reviews/review_id_999
2. MongoDB: Delete review
3. Redis: DELETE user:123:book:42:review
4. Redis: DELETE user:123:book:42:no_review
5. Redis: Now next POST will miss cache → check DB → not found
6. Response: 200 OK
```

#### Scenario 5: Popular Book, First-Time Review for User
```
1. Request: POST /api/reviews { book_id: 42, rating: 5, ... }
2. Redis: Check cache → MISS
3. Redis: Check negative cache user:123:book:42:no_review → MISS
4. MongoDB: Query → NOT FOUND
5. MongoDB: Insert → SUCCESS
6. Redis: SET positive cache EX 3600
7. Response: 201 Created

Next request from SAME user:
1. Request: POST /api/reviews (same user, same book)
2. Redis: Check positive cache → HIT
3. Response: 409 Conflict (instant)

From DIFFERENT user (same book):
1. Request: POST /api/reviews { book_id: 42, ... } (user 456)
2. Redis: Check cache for user:456:book:42:review → MISS (different user)
3. MongoDB: Query → NOT FOUND (different user)
4. MongoDB: Insert → SUCCESS
5. Response: 201 Created (different user can review)
```

## Event Architecture

### Kafka Topics

```
reviews-events topic:
├─ review.created: Fired when new review is created
├─ review.updated: Fired when review is modified
└─ review.deleted: Fired when review is deleted
```

### Event Payload

```json
{
    "event_type": "review.created",
    "timestamp": "2025-01-01T12:34:56Z",
    "data": {
        "review_id": "507f1f77bcf86cd799439011",
        "book_id": 42,
        "user_id": 123,
        "rating": 5
    }
}
```

### Feed Generator Integration (Upcoming)

The Feed Generator will consume `reviews-events` and enrich with book/author data:

```python
# Feed Generator pseudo-code
@consumer("reviews-events")
async def on_review_created(event):
    # Get review from Review Service
    review = await httpx.get(f"/api/reviews/{event['data']['review_id']}")
    
    # Get book details from Catalog Service
    book = await httpx.get(f"/api/books/{event['data']['book_id']}")
    
    # Get user details from User Service
    user = await httpx.get(f"/api/users/{event['data']['user_id']}")
    
    # Cache enriched data in Redis
    enriched_event = {
        "type": "book_review",
        "review_id": review["id"],
        "rating": review["rating"],
        "content": review["content"],
        "book_title": book["title"],
        "author_name": book["author"]["name"],
        "username": user["username"],
        "created_at": review["created_at"]
    }
    
    await redis.lpush("feed:activity:global", json.dumps(enriched_event))
```

## Cross-Service Communication

### Book Review Service → Book Catalog Service

Book Review Service calls Book Catalog Service to validate book exists before creating review:

```python
# In create_review endpoint
async with httpx.AsyncClient() as client:
    book_response = await client.get(
        f"{BOOK_CATALOG_URL}/api/books/{review.book_id}"
    )
    if book_response.status_code != 200:
        raise HTTPException(404, "Book not found")
```

**Failure Handling**:
- If Book Catalog is down → Return 503 Service Unavailable
- If book doesn't exist → Return 404 Not Found
- Otherwise → Proceed with review creation

## Setup and Deployment

### Local Development (Docker Compose)

Add to `docker-compose.yml`:

```yaml
services:
  book-catalog-service:
    build: ./book-catalog-service
    container_name: book-catalog-service
    ports:
      - "5003:5000"  # Different port to avoid conflicts
    environment:
      - DATABASE_URL=postgresql://user:password@postgres-db:5432/microservices_db
      - CONSUL_HOST=consul-server
      - KAFKA_HOST=kafka:9092
    depends_on:
      - postgres-db
    networks:
      - microservices

  book-review-service:
    build: ./book-review-service
    container_name: book-review-service
    ports:
      - "5004:5000"  # Different port to avoid conflicts
    environment:
      - MONGODB_URL=mongodb://user:password@mongodb:27017
      - MONGODB_DB=reviews_db
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - KAFKA_HOST=kafka:9092
      - CONSUL_HOST=consul-server
      - BOOK_CATALOG_URL=http://book-catalog-service:5000
    depends_on:
      - mongodb
      - redis
      - kafka
    networks:
      - microservices
```

### Traefik Configuration

Add to `api_gateway/dynamic.yml`:

```yaml
http:
  routers:
    book-catalog-router:
      rule: "PathPrefix(`/api/authors`, `/api/books`)"
      service: book-catalog-service
      entryPoints:
        - web

    book-review-router:
      rule: "PathPrefix(`/api/reviews`)"
      service: book-review-service
      entryPoints:
        - web

  services:
    book-catalog-service:
      loadBalancer:
        servers:
          - url: "http://book-catalog-service:5000"

    book-review-service:
      loadBalancer:
        servers:
          - url: "http://book-review-service:5000"
```

## Testing

### Manual Testing: Create Author and Book

```bash
# 1. Create Author
curl -X POST http://localhost/api/authors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Frank Herbert",
    "bio": "American science fiction novelist"
  }'

# Response:
# {
#   "id": 1,
#   "name": "Frank Herbert",
#   "bio": "American science fiction novelist",
#   "created_at": "2025-01-01T00:00:00Z"
# }

# 2. Create Book
curl -X POST http://localhost/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Dune",
    "author_id": 1,
    "isbn": "978-0441172719",
    "genre": "science fiction",
    "publication_year": 1965
  }'

# 3. Search Authors (autocomplete)
curl "http://localhost/api/authors/search?q=frank&limit=5"

# 4. Get Books by Author
curl "http://localhost/api/authors/1/books"
```

### Manual Testing: Create and Update Review

```bash
# 1. Create Review (requires JWT token)
curl -X POST http://localhost/api/reviews \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 42,
    "rating": 5,
    "content": "This was an amazing book!",
    "tags": ["sci-fi", "thought-provoking"],
    "spoiler_warning": false
  }'

# 2. Get User's Review for Book
curl "http://localhost/api/users/123/review-of/42" \
  -H "Authorization: Bearer $TOKEN"

# 3. Update Review
curl -X PUT http://localhost/api/reviews/review_id_999 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 4,
    "content": "Actually, not as good as I thought..."
  }'

# 4. Get All Reviews for a Book
curl "http://localhost/api/books/42/reviews?sort=recent&limit=10"

# 5. Get Book Rating
curl "http://localhost/api/books/42/rating"

# 6. Mark Review as Helpful
curl -X POST http://localhost/api/reviews/review_id_999/mark-helpful \
  -H "Authorization: Bearer $TOKEN"
```

## Performance Considerations

### Cache Hit Rates

- **Best case** (cached): 0.5ms (Redis lookup)
- **Cache miss** (database): 5-10ms (PostgreSQL/MongoDB query)
- **Negative cache**: Reduces DB load for popular books not yet reviewed by user

### Database Queries

**Most frequent queries**:
1. Check uniqueness (with Redis cache first): ~5ms avg
2. Get book by ID (with denormalized author): ~5ms
3. List reviews for book (paginated): ~10ms

**Optimization**:
- Book Catalog: Indexes on (author_id, created_at)
- Reviews: Indexes on (book_id, user_id, created_at)
- Redis: Completely in-memory, no disk I/O

## Future Enhancements

1. **Review Verification**: Mark reviews from book authors as verified
2. **Review Moderation**: Flag/hide inappropriate reviews
3. **Advanced Analytics**: Track which reviews are most helpful
4. **Search Integration**: Full-text search on review content
5. **Recommendation System**: Suggest books based on user's rating history

## Troubleshooting

### Reviews-events Topic Not Consumed

```bash
# Check if topic exists
docker exec -it kafka kafka-topics --list --bootstrap-server kafka:9092

# Create topic if missing
docker exec -it kafka kafka-topics \
  --create \
  --topic reviews-events \
  --bootstrap-server kafka:9092 \
  --partitions 1 \
  --replication-factor 1
```

### Redis Connection Issues

```bash
# Test Redis connection
docker exec -it redis redis-cli ping
# Should return: PONG

# Check Redis keys
docker exec -it redis redis-cli
> KEYS user:*
> GET user:123:book:42:review
```

### MongoDB Uniqueness Not Working

```bash
# Verify unique index exists
docker exec -it mongodb mongosh
> use reviews_db
> db.reviews.getIndexes()
# Should show: [book_id, user_id] unique
```
