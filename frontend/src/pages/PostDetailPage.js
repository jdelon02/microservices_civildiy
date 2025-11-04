import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { postsService } from '../services/api';
import SafeHTMLRenderer from '../components/SafeHTMLRenderer';
import './PostDetailPage.css';

const PostDetailPage = () => {
  const { postId } = useParams();
  const [post, setPost] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [editTags, setEditTags] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();
  const { token, user } = useAuth();

  useEffect(() => {
    const loadPost = async () => {
      try {
        setLoading(true);
        const data = await postsService.get(postId);
        setPost(data);
        setEditTitle(data.title);
        setEditContent(data.content);
        setEditTags(data.tags ? data.tags.join(', ') : '');
      } catch (err) {
        setError(err.message || 'Failed to load post');
      } finally {
        setLoading(false);
      }
    };

    loadPost();
  }, [postId]);

  const handleSaveEdit = async () => {
    if (!editTitle.trim() || !editContent.trim()) {
      setError('Title and content are required');
      return;
    }

    setSaving(true);
    try {
      const tagArray = editTags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0);

      const updated = await postsService.update(token, postId, {
        title: editTitle,
        content: editContent,
        tags: tagArray,
      });

      setPost(updated);
      setIsEditing(false);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to save post');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this post?')) {
      return;
    }

    try {
      setSaving(true);
      await postsService.delete(token, postId);
      navigate('/posts');
    } catch (err) {
      setError(err.message || 'Failed to delete post');
      setSaving(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' at ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const isOwner = user && post && post.user_id === parseInt(user.sub);

  if (loading) {
    return <div className="post-detail-container"><p>Loading post...</p></div>;
  }

  if (!post) {
    return (
      <div className="post-detail-container">
        <div className="error-message">Post not found</div>
        <Link to="/posts" className="back-link">← Back to Posts</Link>
      </div>
    );
  }

  return (
    <main className="post-detail-container">
      <Link to="/posts" className="back-link">← Back to Posts</Link>

      {error && <div className="error-message">{error}</div>}

      <article className="post-detail">
        {isEditing && isOwner ? (
          <div className="edit-form">
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                disabled={saving}
              />
            </div>

            <div className="form-group">
              <label>Content</label>
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                rows="12"
                disabled={saving}
              />
            </div>

            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input
                type="text"
                value={editTags}
                onChange={(e) => setEditTags(e.target.value)}
                disabled={saving}
              />
            </div>

            <div className="edit-actions">
              <button
                className="save-btn"
                onClick={handleSaveEdit}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                className="cancel-btn"
                onClick={() => setIsEditing(false)}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            <header className="post-header">
              <SafeHTMLRenderer html={post.title} className="post-title" />
              <div className="post-meta">
                <span className="post-date">Published {formatDate(post.created_at)}</span>
                {post.updated_at !== post.created_at && (
                  <span className="post-updated">Updated {formatDate(post.updated_at)}</span>
                )}
              </div>
            </header>

            <div className="post-body">
              <SafeHTMLRenderer html={post.content} className="post-content" />
            </div>

            {post.tags && post.tags.length > 0 && (
              <div className="post-tags">
                <h4>Tags:</h4>
                {post.tags.map(tag => (
                  <span key={tag} className="tag">{tag}</span>
                ))}
              </div>
            )}

            {isOwner && (
              <footer className="post-actions">
                <button
                  className="edit-btn"
                  onClick={() => setIsEditing(true)}
                >
                  Edit Post
                </button>
                <button
                  className="delete-btn"
                  onClick={handleDelete}
                >
                  Delete Post
                </button>
              </footer>
            )}
          </>
        )}
      </article>
    </main>
  );
};

export default PostDetailPage;
