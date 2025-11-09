import os
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import httpx

from shared_auth import get_current_user

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres-db:5432/microservices_db")
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul-server")
CONSUL_PORT = os.getenv("CONSUL_PORT", 8500)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup - deferred to avoid import-time issues
engine = None
SessionLocal = None
Base = declarative_base()

def init_engine():
    global engine, SessionLocal
    if engine is None:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy Model
class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    dob = Column(String(10), nullable=True)  # YYYY-MM-DD format
    address = Column(String(500), nullable=True)
    city = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    preferences = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic Models
class UserProfileCreate(BaseModel):
    user_id: Optional[int] = None  # Will be populated from X-User-ID header
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[str] = None

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[str] = None

class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    dob: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    country: Optional[str]
    phone: Optional[str]
    bio: Optional[str]
    preferences: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# FastAPI app
app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

# Self-register with Consul
async def register_with_consul():
    try:
        service_data = {
            "ID": "user-profile-service",
            "Name": "user-profile-service",
            "Address": "user-profile-service",
            "Port": 5000,
            "Check": {
                "HTTP": "http://user-profile-service:5000/health",
                "Interval": "10s",
                "Timeout": "5s"
            },
            "Tags": ["api", "profile"]
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
                "traefik/http/routers/profile/rule": "PathPrefix(`/api/profile`)",
                "traefik/http/routers/profile/service": "user-profile-service",
                "traefik/http/routers/profile/entrypoints": "web",
                "traefik/http/services/user-profile-service/loadbalancer/servers/0/url": "http://user-profile-service:5000"
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
    init_engine()
    init_db()
    await register_with_consul()

# Routes
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe: Service is ready to accept traffic.
    Verifies database and Consul connectivity.
    """
    health_status = {}
    
    try:
        # Test database connectivity
        db.execute(text("SELECT 1"))
        health_status["database"] = "ok"
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        health_status["database"] = f"failed: {str(e)}"
    
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
    
    # Check if all dependencies are healthy
    if all(v == "ok" for v in health_status.values()):
        return {
            "status": "ready",
            "service": "user-profile-service",
            "dependencies": health_status
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {health_status}"
        )

@app.get("/health/db")
async def db_health_check(db: Session = Depends(get_db)):
    """
    Database health check: Detailed PostgreSQL status.
    Verifies connectivity and basic functionality.
    """
    health = {}
    
    try:
        # PostgreSQL check
        db.execute(text("SELECT 1"))
        db_stats = db.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")).scalar()
        health["database"] = {
            "status": "healthy",
            "tables": db_stats or 0
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Check if database is unhealthy
    if health.get("database", {}).get("status") == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unhealthy: {health}"
        )
    
    return health

@app.post("/api/profile", response_model=UserProfileResponse)
async def create_profile(profile: UserProfileCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new user profile"""
    try:
        user_id = int(current_user["sub"])
        
        # Check if profile already exists
        existing = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists for this user")
        
        # Create profile with user_id from header, override any provided in body
        profile_data = profile.dict(exclude={"user_id"})
        db_profile = UserProfile(user_id=user_id, **profile_data)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        
        return db_profile
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create profile")

@app.get("/api/profile", response_model=UserProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user profile"""
    try:
        user_id = int(current_user["sub"])
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
        
        return profile
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch profile")

@app.put("/api/profile", response_model=UserProfileResponse)
async def update_profile(profile_update: UserProfileUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update user profile"""
    try:
        user_id = int(current_user["sub"])
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
        
        # Update only provided fields
        update_data = profile_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)
        
        profile.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(profile)
        
        return profile
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")

@app.delete("/api/profile")
async def delete_profile(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete user profile"""
    try:
        user_id = int(current_user["sub"])
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
        
        db.delete(profile)
        db.commit()
        
        return {"message": "Profile deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete profile")
