import React, { useState, useRef } from 'react';
import Creatable from 'react-select/creatable';
import debounce from 'lodash.debounce';
import axios from 'axios';
import './BookReviewForm.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

const BookReviewForm = ({ token, onSuccess, onCancel }) => {
  // Author selection
  const [authorInput, setAuthorInput] = useState('');
  const [authors, setAuthors] = useState([]);
  const [selectedAuthor, setSelectedAuthor] = useState(null);
  const [loadingAuthors, setLoadingAuthors] = useState(false);
  const [authorError, setAuthorError] = useState('');

  // Book selection
  const [bookInput, setBookInput] = useState('');
  const [books, setBooks] = useState([]);
  const [selectedBook, setSelectedBook] = useState(null);
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [bookError, setBookError] = useState('');

  // Review content
  const [rating, setRating] = useState(5);
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [spoilerWarning, setSpoilerWarning] = useState(false);

  // Modal states
  const [showAuthorModal, setShowAuthorModal] = useState(false);
  const [showBookModal, setShowBookModal] = useState(false);
  const [newAuthorName, setNewAuthorName] = useState('');
  const [newBookTitle, setNewBookTitle] = useState('');

  // Form states
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Debounced search functions using refs
  const searchAuthorsRef = useRef(
    debounce(async (query) => {
      if (!query || query.length < 1) {
        setAuthors([]);
        return;
      }

      setLoadingAuthors(true);
      setAuthorError('');

      try {
        const response = await axios.get(
          `${API_BASE_URL}/api/authors/search`,
          {
            params: { q: query, limit: 10 },
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        const authorOptions = response.data.map(author => ({
          value: author.id,
          label: author.name,
          ...author,
        }));

        setAuthors(authorOptions);
      } catch (err) {
        setAuthorError(err.response?.data?.detail || 'Failed to search authors');
        setAuthors([]);
      } finally {
        setLoadingAuthors(false);
      }
    }, 300)
  );

  const searchBooksRef = useRef(
    debounce(async (query) => {
      if (!query || query.length < 1) {
        setBooks([]);
        return;
      }

      setLoadingBooks(true);
      setBookError('');

      try {
        const response = await axios.get(
          `${API_BASE_URL}/api/books/search-by-title`,
          {
            params: { q: query, limit: 10 },
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        const bookOptions = response.data.map(book => ({
          value: book.id,
          label: book.title,
          ...book,
        }));

        setBooks(bookOptions);
      } catch (err) {
        setBookError(err.response?.data?.detail || 'Failed to search books');
        setBooks([]);
      } finally {
        setLoadingBooks(false);
      }
    }, 300)
  );

  const handleAuthorInputChange = (inputValue) => {
    setAuthorInput(inputValue);
    searchAuthorsRef.current(inputValue);
  };

  const handleBookInputChange = (inputValue) => {
    setBookInput(inputValue);
    searchBooksRef.current(inputValue);
  };

  const handleAuthorSelect = (option) => {
    if (option.__isNew__) {
      // Open modal to create new author
      setNewAuthorName(option.label);
      setShowAuthorModal(true);
    } else {
      setSelectedAuthor(option);
      setAuthorInput('');
      setAuthors([]);
    }
  };

  const handleBookSelect = (option) => {
    if (option.__isNew__) {
      // Open modal to create new book
      setNewBookTitle(option.label);
      setShowBookModal(true);
    } else {
      setSelectedBook(option);
      setBookInput('');
      setBooks([]);
    }
  };

  const createNewAuthor = async () => {
    if (!newAuthorName.trim()) {
      setError('Author name is required');
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/authors`,
        { name: newAuthorName },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const newAuthor = {
        value: response.data.id,
        label: response.data.name,
        ...response.data,
      };

      setSelectedAuthor(newAuthor);
      setShowAuthorModal(false);
      setNewAuthorName('');
      setError('');
      setSuccessMessage('Author created successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create author');
    } finally {
      setLoading(false);
    }
  };

  const createNewBook = async () => {
    if (!newBookTitle.trim()) {
      setError('Book title is required');
      return;
    }

    if (!selectedAuthor) {
      setError('Please select an author first');
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/books`,
        {
          title: newBookTitle,
          author_id: selectedAuthor.value,
          genre: '',
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const newBook = {
        value: response.data.id,
        label: response.data.title,
        ...response.data,
      };

      setSelectedBook(newBook);
      setShowBookModal(false);
      setNewBookTitle('');
      setError('');
      setSuccessMessage('Book created successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create book');
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    if (!selectedAuthor) {
      setError('Please select an author');
      return false;
    }
    if (!selectedBook) {
      setError('Please select a book');
      return false;
    }
    if (!rating || rating < 1 || rating > 5) {
      setError('Rating must be between 1 and 5');
      return false;
    }
    if (!content.trim()) {
      setError('Review content is required');
      return false;
    }
    if (content.length < 10) {
      setError('Review content must be at least 10 characters');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const tagArray = tags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0);

      const reviewData = {
        book_id: selectedBook.value,
        rating: parseInt(rating, 10),
        content: content,
        tags: tagArray,
        spoiler_warning: spoilerWarning,
      };

      await axios.post(`${API_BASE_URL}/api/reviews`, reviewData, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setSuccessMessage('Review submitted successfully!');
      // Reset form
      setSelectedAuthor(null);
      setSelectedBook(null);
      setRating(5);
      setContent('');
      setTags('');
      setSpoilerWarning(false);

      // Call onSuccess callback
      if (onSuccess) {
        setTimeout(onSuccess, 1500);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setLoading(false);
    }
  };

  const customStyles = {
    control: (base) => ({
      ...base,
      minHeight: '40px',
      borderColor: '#ccc',
      '&:hover': {
        borderColor: '#999',
      },
    }),
    option: (base, state) => ({
      ...base,
      backgroundColor: state.isFocused ? '#e8f0fe' : 'white',
      color: '#333',
      cursor: 'pointer',
    }),
  };

  return (
    <div className="book-review-form-container">
      <form onSubmit={handleSubmit} className="book-review-form">
        <h2>Write a Book Review</h2>

        {error && <div className="error-message">{error}</div>}
        {successMessage && <div className="success-message">{successMessage}</div>}

        {/* Author Selection */}
        <div className="form-group">
          <label htmlFor="author">Author *</label>
          <Creatable
            id="author"
            name="author"
            isClearable
            isSearchable
            isDisabled={loading}
            isLoading={loadingAuthors}
            options={authors}
            value={selectedAuthor}
            onChange={handleAuthorSelect}
            onInputChange={handleAuthorInputChange}
            inputValue={authorInput}
            styles={customStyles}
            placeholder="Search or type author name..."
            formatCreateLabel={(inputValue) => `Create author "${inputValue}"`}
            isMulti={false}
            allowCreateWhileLoading
            className="react-select-container"
            classNamePrefix="react-select"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.target.tagName.match(/textarea|input/i)) {
                e.preventDefault();
              }
            }}
          />
          {authorError && <small className="error-text">{authorError}</small>}
          <small>Search for existing authors or create a new one</small>
        </div>

        {/* Book Selection */}
        <div className="form-group">
          <label htmlFor="book">Book Title * {!selectedAuthor && <span className="disabled-hint">(select author first)</span>}</label>
          <Creatable
            id="book"
            name="book"
            isClearable
            isSearchable
            isDisabled={!selectedAuthor || loading}
            isLoading={loadingBooks}
            options={books}
            value={selectedBook}
            onChange={handleBookSelect}
            onInputChange={handleBookInputChange}
            inputValue={bookInput}
            styles={customStyles}
            placeholder={selectedAuthor ? "Search or type book title..." : "Select author first"}
            formatCreateLabel={(inputValue) => `Create book "${inputValue}"`}
            isMulti={false}
            allowCreateWhileLoading
            className="react-select-container"
            classNamePrefix="react-select"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.target.tagName.match(/textarea|input/i)) {
                e.preventDefault();
              }
            }}
          />
          {bookError && <small className="error-text">{bookError}</small>}
          <small>Search for existing books or create a new one</small>
        </div>

        {/* Rating */}
        <div className="form-group">
          <label htmlFor="rating">Rating * (1-5)</label>
          <div className="rating-input">
            <input
              id="rating"
              type="number"
              min="1"
              max="5"
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              disabled={loading}
              required
            />
            <div className="rating-display">
              {'⭐'.repeat(parseInt(rating))}
            </div>
          </div>
        </div>

        {/* Review Content */}
        <div className="form-group">
          <label htmlFor="content">Your Review *</label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Share your thoughts about this book (minimum 10 characters)..."
            disabled={loading}
            rows="8"
            required
          />
          <small>
            {content.length}/10+ characters - {content.length < 10 ? 'Too short' : 'Ready'}
          </small>
        </div>

        {/* Spoiler Warning */}
        <div className="form-group">
          <label htmlFor="spoiler" className="checkbox-label">
            <input
              id="spoiler"
              type="checkbox"
              checked={spoilerWarning}
              onChange={(e) => setSpoilerWarning(e.target.checked)}
              disabled={loading}
            />
            <span>This review contains spoilers</span>
          </label>
        </div>

        {/* Tags */}
        <div className="form-group">
          <label htmlFor="tags">Tags (comma-separated)</label>
          <input
            id="tags"
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="e.g., fiction, thriller, recommended"
            disabled={loading}
          />
          <small>Optional: separate multiple tags with commas</small>
        </div>

        {/* Form Actions */}
        <div className="form-actions">
          <button
            type="submit"
            disabled={loading}
            className="submit-btn"
          >
            {loading ? 'Submitting...' : 'Submit Review'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="cancel-btn"
          >
            Cancel
          </button>
        </div>
      </form>

      {/* Create Author Modal */}
      {showAuthorModal && (
        <div className="modal-overlay" onClick={() => !loading && setShowAuthorModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Create New Author</h3>
            <div className="form-group">
              <label htmlFor="new-author-name">Author Name</label>
              <input
                id="new-author-name"
                type="text"
                value={newAuthorName}
                onChange={(e) => setNewAuthorName(e.target.value)}
                placeholder="Enter author name"
                disabled={loading}
                autoFocus
              />
            </div>
            <div className="modal-actions">
              <button
                onClick={createNewAuthor}
                disabled={loading}
                className="submit-btn"
              >
                {loading ? 'Creating...' : 'Create Author'}
              </button>
              <button
                onClick={() => setShowAuthorModal(false)}
                disabled={loading}
                className="cancel-btn"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Book Modal */}
      {showBookModal && (
        <div className="modal-overlay" onClick={() => !loading && setShowBookModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Create New Book</h3>
            <div className="form-group">
              <label>Author</label>
              <input
                type="text"
                value={selectedAuthor?.label || ''}
                disabled
                style={{ backgroundColor: '#f5f5f5' }}
              />
            </div>
            <div className="form-group">
              <label htmlFor="new-book-title">Book Title</label>
              <input
                id="new-book-title"
                type="text"
                value={newBookTitle}
                onChange={(e) => setNewBookTitle(e.target.value)}
                placeholder="Enter book title"
                disabled={loading}
                autoFocus
              />
            </div>
            <div className="modal-actions">
              <button
                onClick={createNewBook}
                disabled={loading}
                className="submit-btn"
              >
                {loading ? 'Creating...' : 'Create Book'}
              </button>
              <button
                onClick={() => setShowBookModal(false)}
                disabled={loading}
                className="cancel-btn"
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
