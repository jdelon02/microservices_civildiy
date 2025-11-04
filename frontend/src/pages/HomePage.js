import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { postsService, feedService } from '../services/api';
import RichTextEditor from '../components/RichTextEditor';
import FeedCard from '../components/FeedCard';
import './HomePage.css';

const HomePage = () => {
  const { isAuthenticated, token, user } = useAuth();
  
  // Post creation state
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [postError, setPostError] = useState('');
  const [postLoading, setPostLoading] = useState(false);
  
  // Feed state
  const [activities, setActivities] = useState([]);
  const [feedLoading, setFeedLoading] = useState(true);
  const [feedError, setFeedError] = useState('');
  const [limit] = useState(50);
  const [skip, setSkip] = useState(0);

  // Load activity feed
  useEffect(() => {
    const loadActivityStream = async () => {
      try {
        setFeedLoading(true);
        const data = await feedService.getGlobal(token, limit, skip);
        setActivities(data.items || []);
      } catch (err) {
        setFeedError(err.message || 'Failed to load activity stream');
      } finally {
        setFeedLoading(false);
      }
    };

    if (isAuthenticated && token) {
      loadActivityStream();
    }
  }, [skip, limit, token, isAuthenticated]);

  const validateForm = () => {
    if (!title.trim()) {
      setPostError('Title is required');
      return false;
    }
    if (!content.trim()) {
      setPostError('Content is required');
      return false;
    }
    if (title.length < 3) {
      setPostError('Title must be at least 3 characters');
      return false;
    }
    if (content.length < 10) {
      setPostError('Content must be at least 10 characters');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setPostError('');

    if (!validateForm()) {
      return;
    }

    setPostLoading(true);

    try {
      const tagArray = tags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0);

      await postsService.create(token, title, content, tagArray);
      
      // Reset form
      setTitle('');
      setContent('');
      setTags('');
      
      // Reload feed from the beginning
      setSkip(0);
      const data = await feedService.getGlobal(token, limit, 0);
      setActivities(data.items || []);
    } catch (err) {
      setPostError(err.message || 'Failed to create post');
    } finally {
      setPostLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (!isAuthenticated) {
    return (
      <main className="home-container">
        <section className="hero">
          <h2>Welcome to CivilDIY</h2>
          <p>Share your DIY projects, learn from others, and build together.</p>
        </section>
        
        <section className="features">
          <div className="feature">
            <h3>📝 Create Posts</h3>
            <p>Share your DIY projects with detailed descriptions and photos</p>
          </div>
          <div className="feature">
            <h3>🔄 Activity Feed</h3>
            <p>Stay updated with the latest projects from the community</p>
          </div>
          <div className="feature">
            <h3>👤 User Profiles</h3>
            <p>Build your profile and showcase your expertise</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="home-container">
      {/* Post Creation Section */}
      <section className="post-creation-section">
        <div className="post-creation-card">
          <h2>What's on your mind?</h2>
          
          {postError && <div className="error-message">{postError}</div>}
          
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="title">Title</label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter post title"
                required
                disabled={postLoading}
              />
              <small>Minimum 3 characters</small>
            </div>

            <div className="form-group">
              <label htmlFor="content">Content</label>
              <RichTextEditor
                value={content}
                onChange={setContent}
                placeholder="Write your post content here (minimum 10 characters)..."
              />
              <small>Minimum 10 characters - Use the toolbar above to format your content</small>
            </div>

            <div className="form-group">
              <label htmlFor="tags">Tags (comma-separated)</label>
              <input
                id="tags"
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="e.g., diy, woodworking, tutorial"
                disabled={postLoading}
              />
              <small>Optional: separate multiple tags with commas</small>
            </div>

            <div className="form-actions">
              <button 
                type="submit" 
                disabled={postLoading}
                className="submit-btn"
              >
                {postLoading ? 'Publishing...' : 'Publish Post'}
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* Activity Feed Section */}
      <section className="feed-section">
        <div className="feed-header">
          <h2>🔥 Happening Now</h2>
          <p>Live activity from the community</p>
        </div>

        {feedError && <div className="error-message">{feedError}</div>}

        {feedLoading && activities.length === 0 ? (
          <div className="loading-message">Loading activity stream...</div>
        ) : activities.length === 0 ? (
          <div className="no-activities">
            <p>No activity yet. Be the first to create something!</p>
          </div>
        ) : (
          <div className="activities-list">
            {activities.map((activity, index) => (
              <FeedCard
                key={`${activity.post_id}-${activity.timestamp}-${index}`}
                activity={activity}
                formatDate={formatDate}
              />
            ))}
          </div>
        )}

        <div className="pagination">
          <button
            onClick={() => setSkip(Math.max(0, skip - limit))}
            disabled={skip === 0}
            className="pagination-btn"
          >
            ← Previous
          </button>
          <span className="pagination-info">
            Showing {skip + 1} - {skip + activities.length}
          </span>
          <button
            onClick={() => setSkip(skip + limit)}
            disabled={activities.length < limit}
            className="pagination-btn"
          >
            Next →
          </button>
        </div>
      </section>
    </main>
  );
};

export default HomePage;
