import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import difflib

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import httpx

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres-db:5432/microservices_db")
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul-server")
CONSUL_PORT = os.getenv("CONSUL_PORT", 8500)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI app
app = FastAPI(title="Book Catalog Service")

# ============================================================================
# SQLAlchemy Models
# ============================================================================

class AuthorDB(Base):
    __tablename__ = "authors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), unique=True, index=True, nullable=False)
    bio = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class BookDB(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    normalized_title = Column(String(255), index=True, nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False, index=True)
    isbn = Column(String(20), unique=True, nullable=True, index=True)
    genre = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    publication_year = Column(Integer, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# Create tables
Base.metadata.create_all(bind=engine)

# ============================================================================
# Pydantic Models
# ============================================================================

class AuthorCreate(BaseModel):
    name: str
    bio: Optional[str] = None

class AuthorUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None

class AuthorResponse(BaseModel):
    id: int
    name: str
    bio: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookCreate(BaseModel):
    title: str
    author_id: int
    isbn: Optional[str] = None
    genre: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    publication_year: Optional[int] = None

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author_id: Optional[int] = None
    isbn: Optional[str] = None
    genre: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    publication_year: Optional[int] = None

class BookResponse(BaseModel):
    id: int
    title: str
    author_id: int
    isbn: Optional[str]
    genre: Optional[str]
    description: Optional[str]
    cover_image_url: Optional[str]
    publication_year: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BookWithAuthorResponse(BaseModel):
    id: int
    title: str
    author: AuthorResponse
    isbn: Optional[str]
    genre: Optional[str]
    description: Optional[str]
    cover_image_url: Optional[str]
    publication_year: Optional[int]
    created_at: datetime
    updated_at: datetime

# ============================================================================
# Database Dependencies
# ============================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# Name Normalization & Deduplication
# ============================================================================

def parse_author_name(name: str) -> str:
    """
    Parse author name and convert to canonical format.
    Handles variations:
    - "Tom Clancy" -> "Tom Clancy"
    - "Clancy, Tom" -> "Tom Clancy"
    - "CLANCY, TOM" -> "Tom Clancy"
    - "clancy tom" -> "Tom Clancy" (swaps if comma-separated pattern detected)
    
    Returns canonical format: "FirstName LastName" (title case)
    """
    name = name.strip()
    
    # Check if it's in "LastName, FirstName" format
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) == 2:
            last_name, first_name = parts
            # Reconstruct as "FirstName LastName"
            name = f"{first_name} {last_name}"
    
    # Title case each word (handles "tom clancy" -> "Tom Clancy")
    words = name.split()
    canonical = ' '.join(word.capitalize() for word in words)
    return canonical

def normalize_name(name: str) -> str:
    """
    Normalize author/book names for consistent matching/deduplication.
    - Parse name (handle LastName, FirstName format)
    - Convert to lowercase
    - Remove extra spaces
    """
    parsed = parse_author_name(name)
    return ' '.join(parsed.lower().split())

def find_existing_author_by_normalized(query: str, db: Session) -> Optional[AuthorDB]:
    """
    Find existing author by normalized name (exact match on normalized field).
    This ensures "Tom Clancy", "clancy tom", "Clancy, Tom" all resolve to the same author.
    """
    normalized_query = normalize_name(query)
    author = db.query(AuthorDB).filter(AuthorDB.normalized_name == normalized_query).first()
    return author

# ============================================================================
# Self-registration with Consul
# ============================================================================

async def register_with_consul():
    try:
        service_data = {
            "ID": "book-catalog-service",
            "Name": "book-catalog-service",
            "Address": "book-catalog-service",
            "Port": 5000,
            "Check": {
                "HTTP": "http://book-catalog-service:5000/health",
                "Interval": "10s",
                "Timeout": "5s"
            },
            "Tags": ["api", "catalog", "books"]
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
            
            # Register Traefik routing rules with Consul KV for authors endpoints
            traefik_config_authors = {
                "traefik/http/routers/authors/rule": "PathPrefix(`/api/authors`)",
                "traefik/http/routers/authors/service": "book-catalog-service",
                "traefik/http/routers/authors/entrypoints": "web",
                "traefik/http/services/book-catalog-service/loadbalancer/servers/0/url": "http://book-catalog-service:5000"
            }
            
            # Register Traefik routing rules with Consul KV for books endpoints
            traefik_config_books = {
                "traefik/http/routers/books/rule": "PathPrefix(`/api/books`)",
                "traefik/http/routers/books/service": "book-catalog-service",
                "traefik/http/routers/books/entrypoints": "web",
            }
            
            all_configs = {**traefik_config_authors, **traefik_config_books}
            
            for key, value in all_configs.items():
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
    await register_with_consul()

# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ============================================================================
# Author Endpoints
# ============================================================================

@app.post("/api/authors", response_model=AuthorResponse, status_code=status.HTTP_201_CREATED)
async def create_author(author: AuthorCreate, db: Session = Depends(get_db)):
    """Create a new author"""
    
    # Check for existing author by normalized name
    existing_author = find_existing_author_by_normalized(author.name, db)
    if existing_author:
        # Return existing author - prevents duplicates of different name formats
        logger.info(f"Found existing author: '{author.name}' matches stored as '{existing_author.name}'")
        return existing_author
    
    try:
        canonical_name = parse_author_name(author.name)
        db_author = AuthorDB(
            name=canonical_name,  # Store canonical format (e.g., "Tom Clancy" not "Clancy, Tom")
            normalized_name=normalize_name(author.name),
            bio=author.bio,
            created_at=datetime.utcnow()
        )
        db.add(db_author)
        db.commit()
        db.refresh(db_author)
        return db_author
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating author: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create author"
        )

@app.get("/api/authors/search", response_model=List[AuthorResponse])
async def search_authors(q: str, limit: int = 10, db: Session = Depends(get_db)):
    """Search authors by name (autocomplete)
    
    Supports:
    - Case-insensitive search
    - Partial name matching ("tom" matches "Tom Clancy")
    - Name order variations ("clancy tom" matches "Tom Clancy")
    - Fuzzy matching for close variations
    """
    
    if len(q) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 1 character"
        )
    
    try:
        # Case-insensitive search with LIKE
        search_term = f"%{q}%"
        authors = db.query(AuthorDB)\
            .filter(AuthorDB.name.ilike(search_term))\
            .limit(limit)\
            .all()
        
        # Also try fuzzy matching for name order variations
        # This helps find "Tom Clancy" when searching "clancy tom"
        normalized_query = normalize_name(q)
        fuzzy_matches = []
        
        for author in db.query(AuthorDB).all():
            if author not in authors:  # Don't duplicate LIKE results
                normalized_author = normalize_name(author.name)
                ratio = difflib.SequenceMatcher(None, normalized_query, normalized_author).ratio()
                if ratio > 0.6:  # 60% similarity threshold
                    fuzzy_matches.append((author, ratio))
        
        # Sort fuzzy matches by similarity (highest first) and combine with LIKE results
        fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
        fuzzy_results = [author for author, ratio in fuzzy_matches]
        
        combined_results = authors + fuzzy_results
        return combined_results[:limit]
    except Exception as e:
        logger.error(f"Error searching authors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search authors"
        )

@app.get("/api/authors/{author_id}", response_model=AuthorResponse)
async def get_author(author_id: int, db: Session = Depends(get_db)):
    """Get a specific author"""
    
    try:
        author = db.query(AuthorDB).filter(AuthorDB.id == author_id).first()
        if not author:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author not found"
            )
        return author
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching author: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch author"
        )

@app.get("/api/authors", response_model=List[AuthorResponse])
async def list_authors(limit: int = 50, skip: int = 0, db: Session = Depends(get_db)):
    """List all authors with pagination"""
    
    try:
        authors = db.query(AuthorDB)\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        return authors
    except Exception as e:
        logger.error(f"Error listing authors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list authors"
        )

# ============================================================================
# Book Endpoints
# ============================================================================

@app.get("/api/books/titles/autocomplete", response_model=List[str])
async def autocomplete_book_titles(q: str, limit: int = 10, db: Session = Depends(get_db)):
    """Autocomplete book titles for frontend combobox
    
    Returns only unique book titles matching the query.
    Supports:
    - Case-insensitive search
    - Partial title matching
    - Fuzzy matching for typos
    """
    
    if len(q) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 1 character"
        )
    
    try:
        # Case-insensitive search for titles
        search_term = f"%{q}%"
        books = db.query(BookDB.title.distinct())\
            .filter(BookDB.title.ilike(search_term))\
            .order_by(BookDB.title)\
            .limit(limit)\
            .all()
        
        # Extract just the titles
        titles = [book[0] for book in books]
        
        # If we need more results, try fuzzy matching
        if len(titles) < limit:
            normalized_query = normalize_name(q)
            all_books = db.query(BookDB.title.distinct()).all()
            fuzzy_matches = []
            
            for book in all_books:
                title = book[0]
                if title not in titles:  # Don't duplicate
                    normalized_title = normalize_name(title)
                    ratio = difflib.SequenceMatcher(None, normalized_query, normalized_title).ratio()
                    if ratio > 0.6:  # 60% similarity threshold
                        fuzzy_matches.append((title, ratio))
            
            # Sort by similarity and add to results
            fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
            titles.extend([title for title, ratio in fuzzy_matches[:limit - len(titles)]])
        
        return titles
    except Exception as e:
        logger.error(f"Error autocompleting book titles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to autocomplete book titles"
        )

@app.post("/api/books", response_model=BookWithAuthorResponse, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate, db: Session = Depends(get_db)):
    """Create a new book"""
    
    # Verify author exists
    author = db.query(AuthorDB).filter(AuthorDB.id == book.author_id).first()
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Author not found"
        )
    
    # Check if ISBN already exists (if provided)
    if book.isbn:
        existing_isbn = db.query(BookDB).filter(BookDB.isbn == book.isbn).first()
        if existing_isbn:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Book with this ISBN already exists"
            )
    
    try:
        now = datetime.utcnow()
        # Title case the book title for consistency
        canonical_title = book.title.strip().title()
        db_book = BookDB(
            title=canonical_title,  # Store title case format
            normalized_title=normalize_name(book.title),
            author_id=book.author_id,
            isbn=book.isbn,
            genre=book.genre,
            description=book.description,
            cover_image_url=book.cover_image_url,
            publication_year=book.publication_year,
            created_at=now,
            updated_at=now
        )
        db.add(db_book)
        db.commit()
        db.refresh(db_book)
        
        return BookWithAuthorResponse(
            **db_book.__dict__,
            author=author
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create book"
        )

@app.get("/api/books/search-by-title", response_model=List[BookWithAuthorResponse])
async def search_books_by_title(
    q: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Search books by title (optimized for autocomplete)
    
    Returns full book details for books matching the title query.
    Supports:
    - Case-insensitive search
    - Partial title matching
    - Fuzzy matching for typos and variations
    """
    
    if len(q) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 1 character"
        )
    
    try:
        search_term = f"%{q}%"
        books = db.query(BookDB)\
            .filter(BookDB.title.ilike(search_term))\
            .order_by(BookDB.title)\
            .limit(limit)\
            .all()
        
        # If fewer results, try searching by normalized title
        if len(books) < limit:
            normalized_query = normalize_name(q)
            more_books = db.query(BookDB)\
                .filter(BookDB.normalized_title.ilike(f"%{normalized_query}%"))\
                .all()
            # Add unique books not already in results
            for book in more_books:
                if not any(b.id == book.id for b in books):
                    books.append(book)
                    if len(books) >= limit:
                        break
        
        # Fetch authors for each book
        result = []
        for book in books[:limit]:
            author = db.query(AuthorDB).filter(AuthorDB.id == book.author_id).first()
            result.append(BookWithAuthorResponse(
                **book.__dict__,
                author=author
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error searching books by title: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search books"
        )

@app.get("/api/books/search", response_model=List[BookWithAuthorResponse])
async def search_books(
    q: Optional[str] = None,
    author_id: Optional[int] = None,
    genre: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Search books by title, author, or genre"""
    
    try:
        query = db.query(BookDB).join(AuthorDB)
        
        if q:
            search_term = f"%{q}%"
            query = query.filter(BookDB.title.ilike(search_term))
        
        if author_id:
            query = query.filter(BookDB.author_id == author_id)
        
        if genre:
            query = query.filter(BookDB.genre.ilike(f"%{genre}%"))
        
        books = query.limit(limit).all()
        
        # Fetch authors for each book
        result = []
        for book in books:
            author = db.query(AuthorDB).filter(AuthorDB.id == book.author_id).first()
            result.append(BookWithAuthorResponse(
                **book.__dict__,
                author=author
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error searching books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search books"
        )

@app.get("/api/books/{book_id}", response_model=BookWithAuthorResponse)
async def get_book(book_id: int, db: Session = Depends(get_db)):
    """Get a specific book with author details"""
    
    try:
        book = db.query(BookDB).filter(BookDB.id == book_id).first()
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        
        author = db.query(AuthorDB).filter(AuthorDB.id == book.author_id).first()
        
        return BookWithAuthorResponse(
            **book.__dict__,
            author=author
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch book"
        )

@app.get("/api/authors/{author_id}/books", response_model=List[BookWithAuthorResponse])
async def get_books_by_author(
    author_id: int,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    """Get all books by a specific author"""
    
    try:
        # Verify author exists
        author = db.query(AuthorDB).filter(AuthorDB.id == author_id).first()
        if not author:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author not found"
            )
        
        books = db.query(BookDB)\
            .filter(BookDB.author_id == author_id)\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        result = []
        for book in books:
            result.append(BookWithAuthorResponse(
                **book.__dict__,
                author=author
            ))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching books by author: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch books"
        )

@app.get("/api/books", response_model=List[BookWithAuthorResponse])
async def list_books(
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    """List all books with pagination"""
    
    try:
        books = db.query(BookDB)\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        result = []
        for book in books:
            author = db.query(AuthorDB).filter(AuthorDB.id == book.author_id).first()
            result.append(BookWithAuthorResponse(
                **book.__dict__,
                author=author
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error listing books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list books"
        )

@app.put("/api/books/{book_id}", response_model=BookWithAuthorResponse)
async def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    """Update a book"""
    
    try:
        book = db.query(BookDB).filter(BookDB.id == book_id).first()
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        
        # If author_id is being changed, verify new author exists
        if book_update.author_id and book_update.author_id != book.author_id:
            author = db.query(AuthorDB).filter(AuthorDB.id == book_update.author_id).first()
            if not author:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Author not found"
                )
        
        # Update fields
        update_data = book_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(book, field, value)
        
        book.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(book)
        
        author = db.query(AuthorDB).filter(AuthorDB.id == book.author_id).first()
        return BookWithAuthorResponse(
            **book.__dict__,
            author=author
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update book"
        )

@app.delete("/api/books/{book_id}")
async def delete_book(book_id: int, db: Session = Depends(get_db)):
    """Delete a book"""
    
    try:
        book = db.query(BookDB).filter(BookDB.id == book_id).first()
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        
        db.delete(book)
        db.commit()
        
        return {"message": "Book deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete book"
        )
