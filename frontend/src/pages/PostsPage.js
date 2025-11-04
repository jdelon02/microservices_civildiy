import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { postsService } from '../services/api';
import './PostsPage.css';

const PostsPage = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { token, user } = useAuth();

  useEffect(() => {
    const loadPosts = async () => {
      try {
        setLoading(true);
        const data = await postsService.list(token, null, 50, 0);
        setPosts(data);
      } catch (err) {
        setError(err.message || 'Failed to load posts');
      } finally {
        setLoading(false);
      }
    };

    loadPosts();
  }, [token]);

  const handleDelete = async (postId) => {
    if (!window.confirm('Are you sure you want to delete this post?')) {
      return;
    }

    try {
      await postsService.delete(token, postId);
      setPosts(posts.filter(p => p.id !== postId));
    } catch (err) {
      setError(err.message || 'Failed to delete post');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return <div className="posts-container"><p>Loading posts...</p></div>;
  }

  return (
    <main className="posts-container">
      <section className="posts-header">
        <h2>Posts Feed</h2>
        <Link to="/posts/new" className="create-post-btn">
          + Create Post
        </Link>
      </section>

      {error && <div className="error-message">{error}</div>}

      {posts.length === 0 ? (
        <div className="no-posts">
          <p>No posts yet. Be the first to share!</p>
          <Link to="/posts/new" className="cta-button">Create First Post</Link>
        </div>
      ) : (
        <div className="posts-list">
          {posts.map(post => (
            <article key={post.id} className="post-card">
              <div className="post-header">
                <h3>{post.title}</h3>
                <span className="post-date">{formatDate(post.created_at)}</span>
              </div>

              <p className="post-content">{post.content.substring(0, 200)}...</p>

              {post.tags && post.tags.length > 0 && (
                <div className="post-tags">
                  {post.tags.map(tag => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
              )}

              <div className="post-footer">
                <Link to={`/posts/${post.id}`} className="read-more">
                  Read More →
                </Link>

                {user && post.user_id === parseInt(user.sub) && (
                  <div className="post-actions">
                    <Link to={`/posts/${post.id}/edit`} className="edit-btn">
                      Edit
                    </Link>
                    <button
                      className="delete-btn"
                      onClick={() => handleDelete(post.id)}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
};

export default PostsPage;
