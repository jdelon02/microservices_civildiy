import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

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
    name = Column(String(255), unique=True, index=True, nullable=False)
    bio = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class BookDB(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
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
            response = await client.put(
                f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/register",
                json=service_data
            )
            
            if response.status_code == 200:
                logger.info("Successfully registered service with Consul")
            else:
                logger.warning(f"Service registration returned status {response.status_code}")
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
    
    # Check if author already exists
    existing = db.query(AuthorDB).filter(AuthorDB.name == author.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Author '{author.name}' already exists"
        )
    
    try:
        db_author = AuthorDB(
            name=author.name,
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
    """Search authors by name (autocomplete)"""
    
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
        
        return authors
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
    Used for book title typeahead search.
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
        db_book = BookDB(
            title=book.title,
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
    If no results, frontend can suggest creating a new book.
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
