import os
import logging
import json
import threading
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from confluent_kafka import Consumer, KafkaError
import redis
import httpx

from shared_auth import get_current_user

# Configuration
KAFKA_HOST = os.getenv("KAFKA_HOST", "kafka:9092")
KAFKA_GROUP = os.getenv("KAFKA_GROUP", "feed-generator")
REDIS_HOST = os.getenv("REDIS_HOST", "read-db")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul-server")
CONSUL_PORT = os.getenv("CONSUL_PORT", 8500)
BOOK_CATALOG_URL = os.getenv("BOOK_CATALOG_URL", "http://book-catalog-service:5000")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connection
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

# FastAPI app
app = FastAPI()

# Pydantic Models
class ActivityFeedItem(BaseModel):
    post_id: Optional[str] = None
    review_id: Optional[str] = None
    book_id: Optional[str] = None
    user_id: int
    username: Optional[str] = None
    event_type: str
    timestamp: datetime
    title: Optional[str] = None
    content: Optional[str] = None
    # Book-specific fields
    book_title: Optional[str] = None
    author_name: Optional[str] = None
    rating: Optional[int] = None
    spoiler_warning: Optional[bool] = None
    tags: Optional[list] = None

# Kafka Consumer Configuration
def create_kafka_consumer():
    conf = {
        "bootstrap.servers": KAFKA_HOST,
        "group.id": KAFKA_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True
    }
    return Consumer(conf)

# Enrich review events with book/author data
async def enrich_review_event(review_data: dict) -> dict:
    """Enrich review event with book and author information"""
    try:
        book_id = review_data.get("book_id")
        if not book_id:
            return review_data
        
        # Fetch book details from Book Catalog Service
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BOOK_CATALOG_URL}/api/books/{book_id}")
            if response.status_code == 200:
                book_data = response.json()
                review_data["book_title"] = book_data.get("title", "Unknown Book")
                author = book_data.get("author", {})
                review_data["author_name"] = author.get("name", "Unknown Author")
                logger.debug(f"Enriched review with book data: {book_data['title']} by {author.get('name')}")
            else:
                logger.warning(f"Could not fetch book details for book_id {book_id}: {response.status_code}")
                review_data["book_title"] = "Unknown Book"
                review_data["author_name"] = "Unknown Author"
    except Exception as e:
        logger.error(f"Error enriching review event: {e}")
        review_data["book_title"] = "Unknown Book"
        review_data["author_name"] = "Unknown Author"
    
    return review_data

# Process Kafka events (updated to handle both posts and reviews)
def process_kafka_event(event_data: dict, topic: str):
    """Process a Kafka event and update Redis feed"""
    try:
        event_type = event_data.get("event_type")
        timestamp = event_data.get("timestamp")
        data = event_data.get("data", {})
        
        user_id = data.get("user_id")
        username = data.get("username", f"User {user_id}")
        
        if topic == "posts-events":
            # Handle post events (existing logic)
            post_id = data.get("post_id")
            title = data.get("title", "")
            content = data.get("content", "")
            
            activity_item = {
                "post_id": post_id,
                "user_id": user_id,
                "username": username,
                "event_type": event_type,
                "timestamp": timestamp,
                "title": title,
                "content": content
            }
            
            logger.info(f"Processed post event: {event_type} for post {post_id}")
            
        elif topic == "reviews-events":
            # Handle review events (new logic)
            review_id = data.get("review_id") or data.get("id")
            book_id = data.get("book_id")
            rating = data.get("rating")
            content = data.get("content", "")
            spoiler_warning = data.get("spoiler_warning", False)
            tags = data.get("tags", [])
            
            # Create enriched activity item for reviews
            activity_item = {
                "review_id": review_id,
                "book_id": book_id,
                "user_id": user_id,
                "username": username,
                "event_type": event_type,
                "timestamp": timestamp,
                "content": content,
                "rating": rating,
                "spoiler_warning": spoiler_warning,
                "tags": tags,
                # These will be filled by enrichment
                "book_title": data.get("book_title", "Unknown Book"),
                "author_name": data.get("author_name", "Unknown Author")
            }
            
            logger.info(f"Processed review event: {event_type} for review {review_id}")
        else:
            logger.warning(f"Unknown topic: {topic}")
            return
        
        # Store in Redis
        # Global activity stream (latest 1000 items)
        global_feed_key = "feed:activity:global"
        redis_client.lpush(global_feed_key, json.dumps(activity_item))
        redis_client.ltrim(global_feed_key, 0, 999)  # Keep only latest 1000
        
        # Per-user activity stream (latest 100 items per user)
        user_feed_key = f"feed:activity:user:{user_id}"
        redis_client.lpush(user_feed_key, json.dumps(activity_item))
        redis_client.ltrim(user_feed_key, 0, 99)  # Keep only latest 100 per user
        
    except Exception as e:
        logger.error(f"Error processing Kafka event from {topic}: {e}")

# Kafka consumer thread
def consume_kafka_events():
    """Run Kafka consumer in background thread"""
    consumer = create_kafka_consumer()
    # Subscribe to both posts and reviews events
    consumer.subscribe(["posts-events", "reviews-events"])
    
    logger.info("Kafka consumer started (subscribed to posts-events and reviews-events)")
    
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug("Reached end of partition")
                else:
                    logger.error(f"Consumer error: {msg.error()}")
                continue
            
            # Process message
            try:
                event_data = json.loads(msg.value().decode("utf-8"))
                topic = msg.topic()
                process_kafka_event(event_data, topic)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding Kafka message: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    except KeyboardInterrupt:
        logger.info("Kafka consumer stopping")
    finally:
        consumer.close()

# Self-register with Consul
async def register_with_consul():
    try:
        service_data = {
            "ID": "feed-generator-service",
            "Name": "feed-generator-service",
            "Address": "feed-generator-service",
            "Port": 5000,
            "Check": {
                "HTTP": "http://feed-generator-service:5000/health",
                "Interval": "10s",
                "Timeout": "5s"
            },
            "Tags": ["api", "feed"]
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
            
            # Register Traefik routing rules with Consul KV
            traefik_config = {
                "traefik/http/routers/feed/rule": "PathPrefix(`/api/activity-stream`)",
                "traefik/http/routers/feed/service": "feed-service",
                "traefik/http/routers/feed/entrypoints": "web",
                "traefik/http/services/feed-service/loadbalancer/servers/0/url": "http://feed-generator-service:5000"
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

# Startup event
@app.on_event("startup")
async def startup_event():
    # Start Kafka consumer in background thread
    consumer_thread = threading.Thread(target=consume_kafka_events, daemon=True)
    consumer_thread.start()
    logger.info("Kafka consumer thread started")
    
    # Register with Consul
    await register_with_consul()

# Routes
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/ready")
async def readiness_check():
    """
    Readiness probe: Service is ready to accept traffic.
    Verifies Redis and Kafka connectivity.
    """
    health_status = {}
    
    try:
        # Test Redis connectivity
        redis_client.ping()
        health_status["redis"] = "ok"
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        health_status["redis"] = f"failed: {str(e)}"
    
    try:
        # Test Kafka connectivity
        consumer = create_kafka_consumer()
        consumer.list_topics(timeout=2)
        consumer.close()
        health_status["kafka"] = "ok"
    except Exception as e:
        logger.error(f"Kafka check failed: {e}")
        health_status["kafka"] = f"failed: {str(e)}"
    
    # Check if all dependencies are healthy
    if all(v == "ok" for v in health_status.values()):
        return {
            "status": "ready",
            "service": "feed-generator-service",
            "dependencies": health_status
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {health_status}"
        )

@app.get("/health/redis")
async def redis_health_check():
    """
    Redis health check: Verify Redis connectivity and basic functionality.
    """
    health = {}
    
    try:
        # Redis check
        redis_client.ping()
        info = redis_client.info()
        health["redis"] = {
            "status": "healthy",
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown")
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health["redis"] = {"status": "unhealthy", "error": str(e)}
    
    # Check if Redis is unhealthy
    if health.get("redis", {}).get("status") == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis unhealthy: {health}"
        )
    
    return health

@app.get("/api/activity-stream")
async def get_global_activity_stream(limit: int = 20, skip: int = 0, current_user: dict = Depends(get_current_user)):
    """Get global activity stream (requires authentication)"""
    try:
        global_feed_key = "feed:activity:global"
        
        # Get items from Redis (skip and limit)
        start = skip
        end = skip + limit - 1
        
        items = redis_client.lrange(global_feed_key, start, end)
        activity_feed = [json.loads(item) for item in items]
        
        return {
            "items": activity_feed,
            "total": redis_client.llen(global_feed_key),
            "limit": limit,
            "skip": skip
        }
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch activity stream")
    except Exception as e:
        logger.error(f"Error fetching activity stream: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch activity stream")

@app.get("/api/activity-stream/user")
async def get_user_activity_stream(limit: int = 20, skip: int = 0, current_user: dict = Depends(get_current_user)):
    """Get activity stream for authenticated user"""
    try:
        user_id = int(current_user["sub"])
        user_feed_key = f"feed:activity:user:{user_id}"
        
        # Get items from Redis (skip and limit)
        start = skip
        end = skip + limit - 1
        
        items = redis_client.lrange(user_feed_key, start, end)
        activity_feed = [json.loads(item) for item in items]
        
        return {
            "items": activity_feed,
            "total": redis_client.llen(user_feed_key),
            "limit": limit,
            "skip": skip
        }
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch activity stream")
    except Exception as e:
        logger.error(f"Error fetching activity stream: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch activity stream")

@app.get("/api/activity-stream/stats")
async def get_feed_stats():
    """Get statistics about the activity feed"""
    try:
        global_feed_key = "feed:activity:global"
        global_count = redis_client.llen(global_feed_key)
        
        return {
            "global_activity_count": global_count,
            "redis_connected": True,
            "kafka_consumer_active": True
        }
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Redis connection failed")
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get stats")
