import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, EmailStr
import jwt
from passlib.context import CryptContext
import psycopg2
from psycopg2.extras import RealDictCursor
import httpx

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://user:password@postgres-db:5432/microservices_db")
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul-server")
CONSUL_PORT = os.getenv("CONSUL_PORT", 8500)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRATION_HOURS = 24

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI app
app = FastAPI()

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserResponse(BaseModel):
    id: int
    email: str
    username: str

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

# Hash password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Verify password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Create JWT token
def create_access_token(user_id: int, email: str, expires_delta: Optional[timedelta] = None) -> tuple[str, int]:
    if expires_delta is None:
        expires_delta = timedelta(hours=TOKEN_EXPIRATION_HOURS)
    
    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    expires_in = int(expires_delta.total_seconds())
    return encoded_jwt, expires_in

# Decode JWT token
def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# Initialize database with retries
def init_db():
    max_retries = 5
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Database initialized successfully")
            return
        except psycopg2.Error as e:
            logger.error(f"Database initialization error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(3)  # Wait 3 seconds before retrying
            else:
                logger.error("Failed to initialize database after all retries")

# Self-register with Consul
async def register_with_consul():
    try:
        # Service registration
        service_data = {
            "ID": "auth-service",
            "Name": "auth-service",
            "Address": "auth-service",
            "Port": 5000,
            "Check": {
                "HTTP": "http://auth-service:5000/health",
                "Interval": "10s",
                "Timeout": "5s"
            },
            "Tags": ["api", "auth"]
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Register service
            logger.info(f"Attempting to register with Consul at {CONSUL_HOST}:{CONSUL_PORT}")
            response = await client.put(
                f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/register",
                json=service_data
            )
            
            if response.status_code == 200:
                logger.info("Successfully registered service with Consul")
            else:
                logger.warning(f"Service registration returned status {response.status_code}: {response.text}")
            
            # Register Traefik routing rules with Consul KV
            traefik_config = {
                "traefik/http/routers/auth/rule": "Host(`localhost`) && PathPrefix(`/api/auth`)",
                "traefik/http/routers/auth/service": "auth-service",
                "traefik/http/routers/auth/entrypoints": "web",
                "traefik/http/services/auth-service/loadbalancer/servers/0/url": "http://auth-service:5000"
            }
            
            for key, value in traefik_config.items():
                try:
                    response = await client.put(
                        f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/kv/{key}",
                        content=value
                    )
                    if response.status_code == 200:
                        logger.info(f"Registered Traefik config: {key}")
                    else:
                        logger.warning(f"Failed to register {key}: HTTP {response.status_code}")
                except Exception as e:
                    logger.error(f"Exception registering {key}: {type(e).__name__}: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to register with Consul: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

# Startup event
@app.on_event("startup")
async def startup_event():
    init_db()
    await register_with_consul()

# Routes
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/auth/register", response_model=UserResponse)
async def register(user: UserRegister):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = %s OR username = %s", (user.email, user.username))
        if cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
        
        # Hash password and create user
        hashed_password = hash_password(user.password)
        cursor.execute(
            "INSERT INTO users (email, username, password_hash) VALUES (%s, %s, %s) RETURNING id, email, username",
            (user.email, user.username, hashed_password)
        )
        
        conn.commit()
        new_user = cursor.fetchone()
        
        return {
            "id": new_user["id"],
            "email": new_user["email"],
            "username": new_user["username"]
        }
    except psycopg2.IntegrityError as e:
        conn.rollback()
        logger.error(f"Registration integrity error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Registration database error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    except Exception as e:
        conn.rollback()
        logger.error(f"Registration error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Find user by email
        cursor.execute("SELECT id, email, password_hash FROM users WHERE email = %s", (user.email,))
        db_user = cursor.fetchone()
        
        if not db_user or not verify_password(user.password, db_user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        # Create token
        token, expires_in = create_access_token(db_user["id"], db_user["email"])
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/auth/validate")
async def validate_token(authorization: Optional[str] = None):
    """
    Endpoint for Traefik forward auth middleware.
    Returns 200 if token is valid, 401 if invalid.
    Includes X-User-ID and X-User-Email headers for downstream services.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization header")
    
    try:
        # Extract token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization format")
        
        token = parts[1]
        payload = decode_token(token)
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        response = Response(status_code=200)
        response.headers["X-User-ID"] = str(user_id)
        response.headers["X-User-Email"] = email
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
