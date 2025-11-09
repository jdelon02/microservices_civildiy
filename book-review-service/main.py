import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from pymongo import MongoClient, errors as PyMongoError
from bson import ObjectId
import redis
import httpx
from confluent_kafka import Producer

from shared_auth import get_current_user

# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://user:password@mongodb:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "reviews_db")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_DB = os.getenv("REDIS_DB", 0)
KAFKA_HOST = os.getenv("KAFKA_HOST", "kafka:9092")
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul-server")
CONSUL_PORT = os.getenv("CONSUL_PORT", 8500)
BOOK_CATALOG_URL = os.getenv("BOOK_CATALOG_URL", "http://book-catalog-service:5000")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
mongo_client = MongoClient(MONGODB_URL)
db = mongo_client[MONGODB_DB]
reviews_collection = db["reviews"]

# Redis setup
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    db=int(REDIS_DB),
    decode_responses=True
)

# Kafka producer
kafka_producer = Producer({"bootstrap.servers": KAFKA_HOST})

# FastAPI app
app = FastAPI(title="Book Review Service")

# ============================================================================
# Pydantic Models
# ============================================================================

class ReviewCreate(BaseModel):
    book_id: int
    rating: int  # 1-5
    content: str
    tags: Optional[List[str]] = []
    spoiler_warning: Optional[bool] = False

class ReviewCreateWithBook(BaseModel):
    """Create review with optional book creation"""
    book_id: Optional[int] = None  # Existing book
    # OR create new book:
    book_title: Optional[str] = None
    author_id: Optional[int] = None
    author_name: Optional[str] = None  # If creating new author
    isbn: Optional[str] = None
    genre: Optional[str] = None
    publication_year: Optional[int] = None
    # Review fields
    rating: int
    content: str
    tags: Optional[List[str]] = []
    spoiler_warning: Optional[bool] = False

class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    spoiler_warning: Optional[bool] = None

class ReviewResponse(BaseModel):
    id: str
    book_id: int
    user_id: int
    rating: int
    content: str
    tags: List[str]
    spoiler_warning: bool
    helpful_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            ObjectId: str
        }

class ReviewBookResponse(BaseModel):
    """Review with book details (for enriched responses)"""
    id: str
    book_id: int
    user_id: int
    rating: int
    content: str
    tags: List[str]
    spoiler_warning: bool
    helpful_count: int
    created_at: datetime
    updated_at: datetime
    book_title: Optional[str] = None
    author_name: Optional[str] = None

# ============================================================================
# Helper Functions
# ============================================================================

def document_to_response(doc) -> ReviewResponse:
    return ReviewResponse(
        id=str(doc["_id"]),
        book_id=doc["book_id"],
        user_id=doc["user_id"],
        rating=doc["rating"],
        content=doc["content"],
        tags=doc.get("tags", []),
        spoiler_warning=doc.get("spoiler_warning", False),
        helpful_count=doc.get("helpful_count", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"]
    )

# ============================================================================
# Redis Cache Functions
# ============================================================================

async def check_review_exists_redis(user_id: int, book_id: int) -> Optional[str]:
    """
    Check if user has reviewed this book using Redis cache.
    Returns review_id if exists, None otherwise.
    
    Cache strategy:
    - Positive: Cache exists for 1 hour (review likely won't change often)
    - Negative: Cache missing for 5 minutes (reduces DB hits for popular books)
    """
    cache_key = f"user:{user_id}:book:{book_id}:review"
    
    try:
        cached_review_id = redis_client.get(cache_key)
        if cached_review_id:
            return cached_review_id
        
        # Check negative cache
        negative_key = f"user:{user_id}:book:{book_id}:no_review"
        if redis_client.exists(negative_key):
            return None
        
        # Not in cache, need to check database
        return None
    except Exception as e:
        logger.warning(f"Redis cache error: {e}, falling back to database")
        return None

async def cache_review_exists_redis(user_id: int, book_id: int, review_id: str):
    """Cache that user has reviewed this book"""
    cache_key = f"user:{user_id}:book:{book_id}:review"
    try:
        redis_client.setex(cache_key, 3600, review_id)  # 1 hour
        
        # Clear negative cache if it exists
        negative_key = f"user:{user_id}:book:{book_id}:no_review"
        redis_client.delete(negative_key)
    except Exception as e:
        logger.warning(f"Error caching review: {e}")

async def cache_review_not_exists_redis(user_id: int, book_id: int):
    """Cache that user has NOT reviewed this book (negative caching)"""
    negative_key = f"user:{user_id}:book:{book_id}:no_review"
    try:
        redis_client.setex(negative_key, 300, "1")  # 5 minutes
    except Exception as e:
        logger.warning(f"Error caching negative: {e}")

async def invalidate_review_cache(user_id: int, book_id: int):
    """Invalidate review cache for a user-book pair"""
    cache_key = f"user:{user_id}:book:{book_id}:review"
    negative_key = f"user:{user_id}:book:{book_id}:no_review"
    try:
        redis_client.delete(cache_key)
        redis_client.delete(negative_key)
    except Exception as e:
        logger.warning(f"Error invalidating cache: {e}")

# ============================================================================
# Database Functions
# ============================================================================

async def check_review_exists_db(user_id: int, book_id: int) -> Optional[str]:
    """Check database for existing review"""
    try:
        review = reviews_collection.find_one({
            "book_id": book_id,
            "user_id": user_id
        })
        return str(review["_id"]) if review else None
    except PyMongoError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check review"
        )

async def has_user_reviewed_book(user_id: int, book_id: int) -> Optional[str]:
    """
    Check if user has reviewed a book (with Redis cache).
    Returns review_id if exists, None otherwise.
    """
    # Try cache first
    cached_id = await check_review_exists_redis(user_id, book_id)
    if cached_id is not None:
        return cached_id if cached_id != "" else None
    
    # Check database
    review_id = await check_review_exists_db(user_id, book_id)
    
    # Update cache
    if review_id:
        await cache_review_exists_redis(user_id, book_id, review_id)
    else:
        await cache_review_not_exists_redis(user_id, book_id)
    
    return review_id

# ============================================================================
# Kafka Publishing
# ============================================================================

def publish_event(event_type: str, review_data: dict):
    """Publish review event to Kafka"""
    try:
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": review_data
        }
        
        kafka_producer.produce(
            topic="reviews-events",
            value=json.dumps(event).encode("utf-8"),
            callback=lambda err, msg: logger.error(f"Kafka error: {err}") if err 
                else logger.info(f"Event published: {event_type}")
        )
        kafka_producer.flush()
    except Exception as e:
        logger.error(f"Error publishing Kafka event: {e}")

# ============================================================================
# Consul Service Registration
# ============================================================================

async def register_with_consul():
    try:
        service_data = {
            "ID": "book-review-service",
            "Name": "book-review-service",
            "Address": "book-review-service",
            "Port": 5000,
            "Check": {
                "HTTP": "http://book-review-service:5000/health",
                "Interval": "10s",
                "Timeout": "5s"
            },
            "Tags": ["api", "reviews", "books"]
        }
        
        async with httpx.AsyncClient() as client:
            # Register service
            response = await client.put(
                f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/register",
                json=service_data
            )
            
            if response.status_code == 200:
                logger.info("Successfully registered service with Consul")
            else:
                logger.warning(f"Service registration returned status {response.status_code}")
            
            # Register Traefik routing rules with Consul KV for reviews endpoints
            traefik_config = {
                "traefik/http/routers/reviews/rule": "PathPrefix(`/api/reviews`)",
                "traefik/http/routers/reviews/service": "book-review-service",
                "traefik/http/routers/reviews/entrypoints": "web",
                "traefik/http/services/book-review-service/loadbalancer/servers/0/url": "http://book-review-service:5000"
            }
            
            for key, value in traefik_config.items():
                try:
                    response = await client.put(
                        f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/kv/{key}",
                        content=value
                    )
                    if response.status_code == 200:
                        logger.info(f"Registered Traefik config: {key}")
                except Exception as e:
                    logger.warning(f"Failed to register {key}: {e}")
    except Exception as e:
        logger.warning(f"Failed to register with Consul: {e}")

# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    try:
        reviews_collection.create_index("book_id")
        reviews_collection.create_index("user_id")
        reviews_collection.create_index("created_at")
        reviews_collection.create_index([("book_id", 1), ("user_id", 1)], unique=True)
        logger.info("Database indexes created")
    except PyMongoError as e:
        logger.error(f"Error creating indexes: {e}")
    
    # Test Redis connection
    try:
        redis_client.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
    
    await register_with_consul()

# ============================================================================
# Health Checks
# ============================================================================

@app.get("/health")
async def health_check():
    """Liveness probe: Service is running"""
    return {
        "status": "healthy",
        "service": "book-review-service",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/ready")
async def readiness_check():
    """
    Readiness probe: Service is ready to accept traffic.
    Verifies all critical dependencies are available:
    - MongoDB connectivity
    - Redis connectivity
    - Consul connectivity
    - Book Catalog Service availability
    """
    health_status = {}
    
    try:
        # Test MongoDB connectivity
        mongo_client.admin.command('ping')
        health_status["mongodb"] = "ok"
    except Exception as e:
        logger.error(f"MongoDB check failed: {e}")
        health_status["mongodb"] = f"failed: {str(e)}"
    
    try:
        # Test Redis connectivity
        redis_client.ping()
        health_status["redis"] = "ok"
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        health_status["redis"] = f"failed: {str(e)}"
    
    try:
        # Test Consul connectivity
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(
                f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/status/leader",
                timeout=2.0
            )
            if response.status_code == 200:
                health_status["consul"] = "ok"
            else:
                health_status["consul"] = f"failed: {response.status_code}"
    except Exception as e:
        logger.error(f"Consul check failed: {e}")
        health_status["consul"] = f"failed: {str(e)}"
    
    try:
        # Test Book Catalog Service availability
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(
                f"{BOOK_CATALOG_URL}/health",
                timeout=2.0
            )
            if response.status_code == 200:
                health_status["book-catalog"] = "ok"
            else:
                health_status["book-catalog"] = f"unavailable: {response.status_code}"
    except Exception as e:
        logger.error(f"Book Catalog check failed: {e}")
        health_status["book-catalog"] = f"unavailable: {str(e)}"
    
    # Check if all dependencies are healthy
    if all(v == "ok" for v in health_status.values()):
        return {
            "status": "ready",
            "service": "book-review-service",
            "dependencies": health_status
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {health_status}"
        )

@app.get("/health/db")
async def db_health_check():
    """
    Database health check: Detailed MongoDB and Redis status.
    Verifies connectivity and basic functionality.
    """
    health = {}
    
    try:
        # MongoDB check with ping
        mongo_client.admin.command('ping')
        
        # Get database stats
        db_stats = mongo_client[MONGODB_DB].command('dbStats')
        health["mongodb"] = {
            "status": "healthy",
            "database": MONGODB_DB,
            "collections": db_stats.get("collections", 0),
            "data_size_bytes": db_stats.get("dataSize", 0),
            "storage_size_bytes": db_stats.get("storageSize", 0)
        }
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        health["mongodb"] = {"status": "unhealthy", "error": str(e)}
    
    try:
        # Redis check with info
        redis_info = redis_client.info()
        health["redis"] = {
            "status": "healthy",
            "connected_clients": redis_info.get("connected_clients", 0),
            "used_memory_mb": redis_info.get("used_memory", 0) / (1024 * 1024),
            "db_keys": redis_client.dbsize()
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health["redis"] = {"status": "unhealthy", "error": str(e)}
    
    # Check if any database is unhealthy
    if any(h.get("status") == "unhealthy" for h in health.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unhealthy: {health}"
        )
    
    return health

# ============================================================================
# Review Endpoints
# ============================================================================

@app.post("/api/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new review"""
    user_id = int(current_user["sub"])
    
    # Validate rating
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    # Verify book exists in Book Catalog Service
    try:
        async with httpx.AsyncClient() as client:
            book_response = await client.get(f"{BOOK_CATALOG_URL}/api/books/{review.book_id}")
            if book_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Book not found"
                )
    except Exception as e:
        logger.error(f"Error validating book: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Book Catalog Service unavailable"
        )
    
    # Check if user already reviewed this book (with cache)
    existing_review_id = await has_user_reviewed_book(user_id, review.book_id)
    if existing_review_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already reviewed this book (Review ID: {existing_review_id}). Use PUT to update."
        )
    
    try:
        now = datetime.utcnow()
        review_data = {
            "book_id": review.book_id,
            "user_id": user_id,
            "rating": review.rating,
            "content": review.content,
            "tags": review.tags or [],
            "spoiler_warning": review.spoiler_warning,
            "helpful_count": 0,
            "created_at": now,
            "updated_at": now
        }
        
        result = reviews_collection.insert_one(review_data)
        review_data["_id"] = result.inserted_id
        
        # Cache the review
        await cache_review_exists_redis(user_id, review.book_id, str(result.inserted_id))
        
        # Publish event
        publish_event("review.created", {
            "review_id": str(result.inserted_id),
            "book_id": review.book_id,
            "user_id": user_id,
            "rating": review.rating
        })
        
        return document_to_response(review_data)
    except PyMongoError as e:
        logger.error(f"Error creating review: {e}")
        
        # If it's a duplicate key error, update cache and return conflict
        if "duplicate" in str(e).lower():
            existing = await check_review_exists_db(user_id, review.book_id)
            if existing:
                await cache_review_exists_redis(user_id, review.book_id, existing)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"You already reviewed this book (Review ID: {existing}). Use PUT to update."
                )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create review"
        )

@app.get("/api/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str):
    """Get a specific review"""
    try:
        review = reviews_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        return document_to_response(review)
    except Exception as e:
        logger.error(f"Error fetching review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch review"
        )

@app.put("/api/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    review_update: ReviewUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update an existing review (ownership verified)"""
    user_id = int(current_user["sub"])
    
    try:
        review = reviews_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        # Verify ownership
        if review["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update another user's review"
            )
        
        # Validate rating if provided
        if review_update.rating is not None:
            if review_update.rating < 1 or review_update.rating > 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rating must be between 1 and 5"
                )
        
        # Update fields
        update_data = review_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        reviews_collection.update_one(
            {"_id": ObjectId(review_id)},
            {"$set": update_data}
        )
        
        updated_review = reviews_collection.find_one({"_id": ObjectId(review_id)})
        
        # Cache is still valid - user still has reviewed this book
        
        # Publish event
        publish_event("review.updated", {
            "review_id": review_id,
            "book_id": review["book_id"],
            "user_id": user_id
        })
        
        return document_to_response(updated_review)
    except (ValueError, Exception) as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error updating review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update review"
        )

@app.delete("/api/reviews/{review_id}")
async def delete_review(
    review_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a review (ownership verified)"""
    user_id = int(current_user["sub"])
    
    try:
        review = reviews_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        # Verify ownership
        if review["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete another user's review"
            )
        
        reviews_collection.delete_one({"_id": ObjectId(review_id)})
        
        # Invalidate cache
        await invalidate_review_cache(user_id, review["book_id"])
        
        # Publish event
        publish_event("review.deleted", {
            "review_id": review_id,
            "book_id": review["book_id"],
            "user_id": user_id
        })
        
        return {"message": "Review deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete review"
        )

@app.get("/api/books/{book_id}/reviews", response_model=List[ReviewResponse])
async def get_book_reviews(
    book_id: int,
    limit: int = 10,
    skip: int = 0,
    sort_by: str = "recent"
):
    """Get all reviews for a book"""
    
    # Verify book exists
    try:
        async with httpx.AsyncClient() as client:
            book_response = await client.get(f"{BOOK_CATALOG_URL}/api/books/{book_id}")
            if book_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Book not found"
                )
    except Exception as e:
        logger.error(f"Error validating book: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Book Catalog Service unavailable"
        )
    
    try:
        sort_field = "helpful_count" if sort_by == "helpful" else "created_at"
        sort_order = -1 if sort_by in ["helpful", "recent"] else 1
        
        reviews = list(
            reviews_collection.find({"book_id": book_id})
            .sort(sort_field, sort_order)
            .limit(limit)
            .skip(skip)
        )
        
        return [document_to_response(review) for review in reviews]
    except PyMongoError as e:
        logger.error(f"Error fetching reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reviews"
        )

@app.get("/api/users/{user_id}/review-of/{book_id}", response_model=ReviewResponse)
async def get_user_review_for_book(user_id: int, book_id: int):
    """Get a specific user's review of a specific book (0 or 1 result)"""
    try:
        review = reviews_collection.find_one({
            "book_id": book_id,
            "user_id": user_id
        })
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User has not reviewed this book"
            )
        
        return document_to_response(review)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch review"
        )

@app.post("/api/reviews/{review_id}/mark-helpful")
async def mark_review_helpful(review_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Mark a review as helpful"""
    try:
        review = reviews_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        # Increment helpful count
        reviews_collection.update_one(
            {"_id": ObjectId(review_id)},
            {"$inc": {"helpful_count": 1}}
        )
        
        updated_review = reviews_collection.find_one({"_id": ObjectId(review_id)})
        return document_to_response(updated_review)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking review helpful: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark review as helpful"
        )

@app.get("/api/books/{book_id}/rating")
async def get_book_rating(book_id: int):
    """Get aggregate rating and review count for a book"""
    try:
        reviews = list(reviews_collection.find({"book_id": book_id}))
        
        if not reviews:
            return {
                "book_id": book_id,
                "average_rating": 0,
                "review_count": 0
            }
        
        total_rating = sum(review["rating"] for review in reviews)
        average_rating = total_rating / len(reviews)
        
        return {
            "book_id": book_id,
            "average_rating": round(average_rating, 2),
            "review_count": len(reviews)
        }
    except PyMongoError as e:
        logger.error(f"Error calculating rating: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate rating"
        )
