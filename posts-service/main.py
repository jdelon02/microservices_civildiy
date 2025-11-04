import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from pymongo import MongoClient, errors as PyMongoError
from bson import ObjectId
from confluent_kafka import Producer
import httpx

from shared_auth import get_current_user

# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://user:password@mongodb:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "posts_db")
KAFKA_HOST = os.getenv("KAFKA_HOST", "kafka:9092")
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul-server")
CONSUL_PORT = os.getenv("CONSUL_PORT", 8500)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
mongo_client = MongoClient(MONGODB_URL)
db = mongo_client[MONGODB_DB]
posts_collection = db["posts"]

# Kafka producer
kafka_producer = Producer({"bootstrap.servers": KAFKA_HOST})

# FastAPI app
app = FastAPI()

# Pydantic Models
class PostCreate(BaseModel):
    title: str
    content: str
    tags: Optional[list[str]] = []

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None

class PostResponse(BaseModel):
    id: str
    user_id: int
    title: str
    content: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            ObjectId: str
        }

# Helper function to convert MongoDB document to response
def document_to_response(doc):
    return PostResponse(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        title=doc["title"],
        content=doc["content"],
        tags=doc.get("tags", []),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"]
    )

# Publish event to Kafka
def publish_event(event_type: str, post_data: dict):
    try:
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": post_data
        }
        
        kafka_producer.produce(
            topic="posts-events",
            value=json.dumps(event).encode("utf-8"),
            callback=lambda err, msg: logger.error(f"Kafka error: {err}") if err else logger.info(f"Event published: {event_type}")
        )
        kafka_producer.flush()
    except Exception as e:
        logger.error(f"Error publishing Kafka event: {e}")

# Self-register with Consul
async def register_with_consul():
    try:
        service_data = {
            "ID": "posts-service",
            "Name": "posts-service",
            "Address": "posts-service",
            "Port": 5000,
            "Check": {
                "HTTP": "http://posts-service:5000/health",
                "Interval": "10s",
                "Timeout": "5s"
            },
            "Tags": ["api", "posts"]
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
                "traefik/http/routers/posts/rule": "PathPrefix(`/api/posts`)",
                "traefik/http/routers/posts/service": "posts-service",
                "traefik/http/routers/posts/entrypoints": "web",
                "traefik/http/services/posts-service/loadbalancer/servers/0/url": "http://posts-service:5000"
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
    # Create indexes
    try:
        posts_collection.create_index("user_id")
        posts_collection.create_index("created_at")
        logger.info("Database indexes created")
    except PyMongoError as e:
        logger.error(f"Error creating indexes: {e}")
    
    await register_with_consul()

# Routes
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/posts", response_model=PostResponse)
async def create_post(post: PostCreate, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Create a new post"""
    user_id = int(current_user["sub"])
    
    try:
        now = datetime.utcnow()
        post_data = {
            "user_id": user_id,
            "title": post.title,
            "content": post.content,
            "tags": post.tags or [],
            "created_at": now,
            "updated_at": now
        }
        
        result = posts_collection.insert_one(post_data)
        post_data["_id"] = result.inserted_id
        
        # Publish event
        publish_event("post.created", {
            "post_id": str(result.inserted_id),
            "user_id": user_id,
            "title": post.title
        })
        
        return document_to_response(post_data)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    except PyMongoError as e:
        logger.error(f"Error creating post: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create post")

@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: str):
    """Get a specific post"""
    try:
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        
        return document_to_response(post)
    except Exception as e:
        logger.error(f"Error fetching post: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch post")

@app.get("/api/posts")
async def list_posts(user_id: Optional[int] = None, limit: int = 10, skip: int = 0):
    """List posts, optionally filtered by user_id"""
    try:
        query = {}
        if user_id:
            query["user_id"] = user_id
        
        posts = list(posts_collection.find(query)
                     .sort("created_at", -1)
                     .limit(limit)
                     .skip(skip))
        
        return [document_to_response(post) for post in posts]
    except PyMongoError as e:
        logger.error(f"Error listing posts: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list posts")

@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post(post_id: str, post_update: PostUpdate, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Update a post (only by owner)"""
    user_id = int(current_user["sub"])
    
    try:
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        
        # Verify ownership
        if post["user_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update another user's post")
        
        # Update fields
        update_data = post_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        posts_collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": update_data}
        )
        
        updated_post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        # Publish event
        publish_event("post.updated", {
            "post_id": post_id,
            "user_id": user_id
        })
        
        return document_to_response(updated_post)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID or post ID format")
    except HTTPException:
        raise
    except PyMongoError as e:
        logger.error(f"Error updating post: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update post")

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Delete a post (only by owner)"""
    user_id = int(current_user["sub"])
    
    try:
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        
        # Verify ownership
        if post["user_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another user's post")
        
        posts_collection.delete_one({"_id": ObjectId(post_id)})
        
        # Publish event
        publish_event("post.deleted", {
            "post_id": post_id,
            "user_id": user_id
        })
        
        return {"message": "Post deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID or post ID format")
    except HTTPException:
        raise
    except PyMongoError as e:
        logger.error(f"Error deleting post: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete post")
