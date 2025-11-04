import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { postsService, feedService } from '../services/api';
import RichTextEditor from './RichTextEditor';
import './CreatePostModal.css';

const CreatePostModal = ({ isOpen, onClose, onPostCreated }) => {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { token } = useAuth();

  const validateForm = () => {
    if (!title.trim()) {
      setError('Title is required');
      return false;
    }
    if (!content.trim()) {
      setError('Content is required');
      return false;
    }
    if (title.length < 3) {
      setError('Title must be at least 3 characters');
      return false;
    }
    if (content.length < 10) {
      setError('Content must be at least 10 characters');
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

      await postsService.create(token, title, content, tagArray);
      
      // Notify parent to refresh feed
      if (onPostCreated) {
        onPostCreated();
      }

      // Reset form and close modal
      setTitle('');
      setContent('');
      setTags('');
      setError('');
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create post');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setTitle('');
      setContent('');
      setTags('');
      setError('');
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={handleClose} disabled={loading}>
          ✕
        </button>

        <h2>Create New Post</h2>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="modal-title">Title</label>
            <input
              id="modal-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter post title"
              required
              disabled={loading}
            />
            <small>Minimum 3 characters</small>
          </div>

          <div className="form-group">
            <label htmlFor="modal-content">Content</label>
            <RichTextEditor
              value={content}
              onChange={setContent}
              placeholder="Write your post content here (minimum 10 characters)..."
            />
            <small>Minimum 10 characters - Use the toolbar above to format your content</small>
          </div>

          <div className="form-group">
            <label htmlFor="modal-tags">Tags (comma-separated)</label>
            <input
              id="modal-tags"
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g., diy, woodworking, tutorial"
              disabled={loading}
            />
            <small>Optional: separate multiple tags with commas</small>
          </div>

          <div className="form-actions">
            <button 
              type="submit" 
              disabled={loading}
              className="submit-btn"
            >
              {loading ? 'Publishing...' : 'Publish Post'}
            </button>
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="cancel-btn"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreatePostModal;
