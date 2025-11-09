# Frontend Implementation: Book Review with Autocomplete

This guide shows how to implement the book review creation form with author and book title autocomplete on the frontend.

## Architecture

```
User Types in Form
    ↓
Frontend State Management
    ├─ Author search input
    ├─ Book search input
    └─ Review content
    ↓
API Calls (debounced)
    ├─ GET /api/authors/search?q=...  → Author suggestions
    └─ GET /api/books/titles/autocomplete?q=...  → Book title suggestions
    ↓
User Selects or Adds New
    ├─ Select existing author OR create new → POST /api/authors
    ├─ Select existing book OR create new → POST /api/books
    └─ (optionally fill in more book metadata)
    ↓
Submit Review
    └─ POST /api/reviews { book_id, rating, content, ... }
```

## Backend Endpoints

### Author Autocomplete
```
GET /api/authors/search?q=stephen&limit=10

Response:
[
  { "id": 1, "name": "Stephen King", "bio": "...", "created_at": "..." },
  { "id": 2, "name": "Stephen Hawking", "bio": "...", "created_at": "..." }
]
```

### Book Title Autocomplete
```
GET /api/books/titles/autocomplete?q=dune&limit=10

Response (just titles):
[
  "Dune",
  "Dune: Messiah",
  "Children of Dune",
  "God Emperor of Dune"
]
```

### Book Search by Title
```
GET /api/books/search-by-title?q=dune&limit=10

Response (full book details):
[
  {
    "id": 42,
    "title": "Dune",
    "author": { "id": 1, "name": "Frank Herbert", "bio": "...", "created_at": "..." },
    "isbn": "978-0441172719",
    "genre": "science fiction",
    "description": "...",
    "cover_image_url": "https://...",
    "publication_year": 1965,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

### Create Author
```
POST /api/authors

Request:
{
  "name": "New Author",
  "bio": "Author biography"
}

Response:
{
  "id": 123,
  "name": "New Author",
  "bio": "...",
  "created_at": "..."
}
```

### Create Book
```
POST /api/books

Request:
{
  "title": "New Book",
  "author_id": 1,
  "isbn": "978-...",
  "genre": "science fiction",
  "description": "...",
  "cover_image_url": "https://...",
  "publication_year": 2025
}

Response:
{
  "id": 456,
  "title": "New Book",
  "author": { ... },
  "isbn": "...",
  "genre": "...",
  "created_at": "...",
  "updated_at": "..."
}
```

### Create Review
```
POST /api/reviews

Request:
{
  "book_id": 42,
  "rating": 5,
  "content": "This book was amazing!",
  "tags": ["sci-fi", "thought-provoking"],
  "spoiler_warning": false
}

Response:
{
  "id": "507f...",
  "book_id": 42,
  "user_id": 123,
  "rating": 5,
  "content": "...",
  "tags": [...],
  "spoiler_warning": false,
  "helpful_count": 0,
  "created_at": "...",
  "updated_at": "..."
}
```

---

## React Implementation Example

### Setup

```bash
npm install react-select axios lodash.debounce
```

### BookReviewForm.jsx

```jsx
import React, { useState, useCallback } from 'react';
import Select from 'react-select';
import debounce from 'lodash.debounce';
import axios from 'axios';

const API_BASE = 'http://localhost';

const BookReviewForm = () => {
  // State
  const [selectedAuthor, setSelectedAuthor] = useState(null);
  const [selectedBook, setSelectedBook] = useState(null);
  const [bookTitle, setBookTitle] = useState('');
  const [rating, setRating] = useState(0);
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [spoilerWarning, setSpoilerWarning] = useState(false);
  
  // Autocomplete state
  const [authorOptions, setAuthorOptions] = useState([]);
  const [bookOptions, setBookOptions] = useState([]);
  const [loadingAuthors, setLoadingAuthors] = useState(false);
  const [loadingBooks, setLoadingBooks] = useState(false);
  
  // Modal states
  const [showAddAuthorModal, setShowAddAuthorModal] = useState(false);
  const [showAddBookModal, setShowAddBookModal] = useState(false);
  const [newAuthorName, setNewAuthorName] = useState('');
  const [newBookData, setNewBookData] = useState({
    title: '',
    isbn: '',
    genre: '',
    publication_year: new Date().getFullYear()
  });
  
  // ============================================================================
  // Autocomplete Functions (Debounced)
  // ============================================================================
  
  const searchAuthors = useCallback(
    debounce(async (query) => {
      if (!query || query.length < 1) {
        setAuthorOptions([]);
        return;
      }
      
      setLoadingAuthors(true);
      try {
        const response = await axios.get(
          `${API_BASE}/api/authors/search?q=${encodeURIComponent(query)}&limit=10`
        );
        
        const options = response.data.map(author => ({
          value: author.id,
          label: author.name,
          data: author
        }));
        
        // Add "Create new" option
        options.push({
          value: '__create_new__',
          label: `+ Add new author "${query}"`,
          isCreate: true,
          inputValue: query
        });
        
        setAuthorOptions(options);
      } catch (error) {
        console.error('Error searching authors:', error);
        setAuthorOptions([]);
      } finally {
        setLoadingAuthors(false);
      }
    }, 300),
    []
  );
  
  const searchBooks = useCallback(
    debounce(async (query) => {
      if (!query || query.length < 1) {
        setBookOptions([]);
        return;
      }
      
      setLoadingBooks(true);
      try {
        const response = await axios.get(
          `${API_BASE}/api/books/search-by-title?q=${encodeURIComponent(query)}&limit=10`
        );
        
        const options = response.data.map(book => ({
          value: book.id,
          label: `${book.title} by ${book.author.name}`,
          data: book
        }));
        
        // Add "Create new" option if no author selected
        if (!selectedAuthor) {
          options.push({
            value: '__create_new__',
            label: `+ Add new book "${query}"`,
            isCreate: true,
            inputValue: query
          });
        }
        
        setBookOptions(options);
      } catch (error) {
        console.error('Error searching books:', error);
        setBookOptions([]);
      } finally {
        setLoadingBooks(false);
      }
    }, 300),
    [selectedAuthor]
  );
  
  // ============================================================================
  // Selection Handlers
  // ============================================================================
  
  const handleAuthorChange = (option) => {
    if (option.isCreate) {
      // Show modal to create new author
      setNewAuthorName(option.inputValue);
      setShowAddAuthorModal(true);
    } else {
      setSelectedAuthor(option);
      // Reset book selection when author changes
      setSelectedBook(null);
      setBookTitle('');
    }
  };
  
  const handleBookChange = (option) => {
    if (option.isCreate) {
      // Show modal to create new book
      setNewBookData({
        ...newBookData,
        title: option.inputValue
      });
      setShowAddBookModal(true);
    } else {
      setSelectedBook(option);
      setBookTitle(option.label);
    }
  };
  
  // ============================================================================
  // Create New Author
  // ============================================================================
  
  const handleCreateAuthor = async () => {
    if (!newAuthorName.trim()) return;
    
    try {
      const response = await axios.post(
        `${API_BASE}/api/authors`,
        { name: newAuthorName, bio: '' },
        { headers: { 'Content-Type': 'application/json' } }
      );
      
      const newAuthor = response.data;
      setSelectedAuthor({
        value: newAuthor.id,
        label: newAuthor.name,
        data: newAuthor
      });
      
      setShowAddAuthorModal(false);
      setNewAuthorName('');
    } catch (error) {
      console.error('Error creating author:', error);
      alert('Failed to create author');
    }
  };
  
  // ============================================================================
  // Create New Book
  // ============================================================================
  
  const handleCreateBook = async () => {
    if (!selectedAuthor) {
      alert('Please select an author first');
      return;
    }
    
    if (!newBookData.title.trim()) {
      alert('Book title is required');
      return;
    }
    
    try {
      const response = await axios.post(
        `${API_BASE}/api/books`,
        {
          title: newBookData.title,
          author_id: selectedAuthor.value,
          isbn: newBookData.isbn || null,
          genre: newBookData.genre || null,
          publication_year: newBookData.publication_year || null
        },
        { headers: { 'Content-Type': 'application/json' } }
      );
      
      const newBook = response.data;
      setSelectedBook({
        value: newBook.id,
        label: `${newBook.title} by ${newBook.author.name}`,
        data: newBook
      });
      
      setShowAddBookModal(false);
      setNewBookData({
        title: '',
        isbn: '',
        genre: '',
        publication_year: new Date().getFullYear()
      });
    } catch (error) {
      console.error('Error creating book:', error);
      alert('Failed to create book');
    }
  };
  
  // ============================================================================
  // Submit Review
  // ============================================================================
  
  const handleSubmitReview = async (e) => {
    e.preventDefault();
    
    if (!selectedBook) {
      alert('Please select a book');
      return;
    }
    
    if (!rating || rating < 1 || rating > 5) {
      alert('Please select a rating (1-5 stars)');
      return;
    }
    
    if (!content.trim() || content.length < 10) {
      alert('Review content must be at least 10 characters');
      return;
    }
    
    try {
      const tagArray = tags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0);
      
      const response = await axios.post(
        `${API_BASE}/api/reviews`,
        {
          book_id: selectedBook.value,
          rating: parseInt(rating),
          content: content.trim(),
          tags: tagArray,
          spoiler_warning: spoilerWarning
        },
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      alert('Review posted successfully!');
      // Reset form
      setSelectedAuthor(null);
      setSelectedBook(null);
      setRating(0);
      setContent('');
      setTags('');
      setSpoilerWarning(false);
    } catch (error) {
      console.error('Error submitting review:', error);
      alert(error.response?.data?.detail || 'Failed to submit review');
    }
  };
  
  // ============================================================================
  // Render
  // ============================================================================
  
  return (
    <div className="book-review-form">
      <h2>Write a Book Review</h2>
      
      <form onSubmit={handleSubmitReview}>
        
        {/* Step 1: Select Author */}
        <div className="form-group">
          <label>Author</label>
          <Select
            options={authorOptions}
            value={selectedAuthor}
            onChange={handleAuthorChange}
            onInputChange={(input) => {
              if (input.length >= 1) {
                searchAuthors(input);
              }
            }}
            isLoading={loadingAuthors}
            isClearable
            placeholder="Search for an author..."
            noOptionsMessage={() => "No authors found. Type to add new."}
          />
        </div>
        
        {/* Step 2: Select or Create Book */}
        <div className="form-group">
          <label>Book Title</label>
          <Select
            options={bookOptions}
            value={selectedBook}
            onChange={handleBookChange}
            onInputChange={(input) => {
              setBookTitle(input);
              if (input.length >= 1) {
                searchBooks(input);
              }
            }}
            isLoading={loadingBooks}
            isClearable
            isDisabled={!selectedAuthor}
            placeholder={selectedAuthor ? "Search for a book..." : "Select an author first"}
            noOptionsMessage={() => "No books found. Type to add new."}
          />
        </div>
        
        {/* Step 3: Rating */}
        <div className="form-group">
          <label>Rating</label>
          <div className="rating-selector">
            {[1, 2, 3, 4, 5].map(star => (
              <button
                key={star}
                type="button"
                className={`star ${rating >= star ? 'active' : ''}`}
                onClick={() => setRating(star)}
              >
                ★
              </button>
            ))}
          </div>
        </div>
        
        {/* Step 4: Review Content */}
        <div className="form-group">
          <label>Review</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Write your review (at least 10 characters)..."
            rows="6"
            minLength="10"
            required
          />
        </div>
        
        {/* Tags */}
        <div className="form-group">
          <label>Tags (comma-separated)</label>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="e.g., sci-fi, thought-provoking, must-read"
          />
        </div>
        
        {/* Spoiler Warning */}
        <div className="form-group checkbox">
          <label>
            <input
              type="checkbox"
              checked={spoilerWarning}
              onChange={(e) => setSpoilerWarning(e.target.checked)}
            />
            This review contains spoilers
          </label>
        </div>
        
        {/* Submit Button */}
        <button type="submit" className="btn-primary" disabled={!selectedBook}>
          Post Review
        </button>
      </form>
      
      {/* Modal: Create New Author */}
      {showAddAuthorModal && (
        <div className="modal">
          <div className="modal-content">
            <h3>Add New Author</h3>
            <input
              type="text"
              value={newAuthorName}
              onChange={(e) => setNewAuthorName(e.target.value)}
              placeholder="Author name"
            />
            <div className="modal-actions">
              <button onClick={handleCreateAuthor} className="btn-primary">
                Create
              </button>
              <button
                onClick={() => setShowAddAuthorModal(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Modal: Create New Book */}
      {showAddBookModal && (
        <div className="modal">
          <div className="modal-content">
            <h3>Add New Book</h3>
            <input
              type="text"
              value={newBookData.title}
              onChange={(e) =>
                setNewBookData({ ...newBookData, title: e.target.value })
              }
              placeholder="Book title"
            />
            <input
              type="text"
              value={newBookData.isbn}
              onChange={(e) =>
                setNewBookData({ ...newBookData, isbn: e.target.value })
              }
              placeholder="ISBN (optional)"
            />
            <input
              type="text"
              value={newBookData.genre}
              onChange={(e) =>
                setNewBookData({ ...newBookData, genre: e.target.value })
              }
              placeholder="Genre (optional)"
            />
            <input
              type="number"
              value={newBookData.publication_year}
              onChange={(e) =>
                setNewBookData({
                  ...newBookData,
                  publication_year: parseInt(e.target.value)
                })
              }
              placeholder="Publication year (optional)"
            />
            <div className="modal-actions">
              <button onClick={handleCreateBook} className="btn-primary">
                Create
              </button>
              <button
                onClick={() => setShowAddBookModal(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BookReviewForm;
```

### CSS Styling

```css
.book-review-form {
  max-width: 600px;
  margin: 20px auto;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-family: inherit;
}

.form-group textarea {
  resize: vertical;
}

.rating-selector {
  display: flex;
  gap: 10px;
}

.star {
  background: none;
  border: none;
  font-size: 32px;
  cursor: pointer;
  color: #ddd;
  transition: color 0.2s;
}

.star.active {
  color: #ffc107;
}

.star:hover {
  color: #ffc107;
}

.checkbox {
  display: flex;
  align-items: center;
}

.checkbox input {
  width: auto;
  margin-right: 10px;
}

.btn-primary {
  background-color: #007bff;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
}

.btn-primary:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 10px;
}

.btn-secondary:hover {
  background-color: #545b62;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  max-width: 400px;
  width: 90%;
}

.modal-content h3 {
  margin-top: 0;
}

.modal-content input {
  width: 100%;
  padding: 10px;
  margin-bottom: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
```

---

## Usage Flow

### Scenario 1: Review Existing Book

```
1. User starts typing in author field
2. Frontend calls: GET /api/authors/search?q=frank
3. Shows dropdown with "Frank Herbert" + "Add new author" option
4. User clicks "Frank Herbert"
5. User starts typing in book field
6. Frontend calls: GET /api/books/search-by-title?q=dune
7. Shows dropdown with existing books by that author
8. User clicks "Dune"
9. User fills in rating, review, tags
10. User clicks "Post Review"
11. Frontend calls: POST /api/reviews with book_id=42
```

### Scenario 2: Review New Book by Existing Author

```
1. User selects "Frank Herbert" from author autocomplete
2. User types book title "New Book" in book field
3. Frontend shows only "Dune" and other existing books (no autocomplete match)
4. User sees "Add new book 'New Book'" option
5. User clicks it → Modal appears
6. User fills in ISBN, genre, publication year
7. User clicks "Create"
8. New book is created and selected
9. User completes review form and submits
```

### Scenario 3: Review Book by New Author

```
1. User types author name in author field
2. No results found
3. User sees "Add new author" option
4. User clicks it → Modal appears
5. User clicks "Create"
6. Author is created and selected
7. User types book title in book field
8. Sees "Add new book" option
9. User clicks it → Modal appears
10. User fills in book details
11. User clicks "Create"
12. Book is created and selected
13. User completes review form and submits
```

---

## Error Handling

```jsx
// Handle duplicate review error
try {
  const response = await axios.post('/api/reviews', reviewData);
} catch (error) {
  if (error.response?.status === 409) {
    alert('You already reviewed this book! Use the update endpoint instead.');
  } else if (error.response?.status === 503) {
    alert('Book Catalog Service is unavailable. Please try again later.');
  } else {
    alert('Failed to submit review');
  }
}

// Handle author creation error (duplicate)
try {
  const response = await axios.post('/api/authors', { name: authorName });
} catch (error) {
  if (error.response?.status === 409) {
    alert('This author already exists! Please select them from the dropdown.');
  }
}

// Handle book creation error (duplicate ISBN)
try {
  const response = await axios.post('/api/books', bookData);
} catch (error) {
  if (error.response?.status === 409) {
    alert('A book with this ISBN already exists.');
  }
}
```

---

## Performance Tips

1. **Debounce Searches**: Already done (300ms debounce)
2. **Limit Results**: Cap at 10 results per search
3. **Cache Results**: Consider caching author/book searches locally
4. **Lazy Loading**: Only fetch on user input, not on page load
5. **Async Operations**: Don't block UI during API calls

---

## Accessibility

```jsx
// Add proper ARIA labels
<Select
  options={authorOptions}
  aria-label="Search and select author"
  inputId="author-select"
  aria-describedby="author-help"
/>
<div id="author-help">Start typing to search for authors</div>
```

---

## Summary

The autocomplete flow provides:
- ✅ Search existing authors/books
- ✅ Create new authors inline
- ✅ Create new books inline
- ✅ Proper error handling
- ✅ User-friendly UX with modals
- ✅ Debounced searches for performance
