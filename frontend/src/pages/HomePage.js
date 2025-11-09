import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { feedService } from '../services/api';
import CreateChoiceModal from '../components/CreateChoiceModal';
import CreatePostModal from '../components/CreatePostModal';
import FeedCard from '../components/FeedCard';
import './HomePage.css';

const HomePage = () => {
  const { isAuthenticated, token } = useAuth();
  const navigate = useNavigate();
  
  // Modal state
  const [isChoiceModalOpen, setIsChoiceModalOpen] = useState(false);
  const [isPostModalOpen, setIsPostModalOpen] = useState(false);
  
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

  const handlePostCreated = async () => {
    // Reload feed from the beginning
    setSkip(0);
    try {
      const data = await feedService.getGlobal(token, limit, 0);
      setActivities(data.items || []);
    } catch (err) {
      setFeedError(err.message || 'Failed to reload feed');
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
      {/* Floating Action Button */}
      <button 
        className="fab-button" 
        onClick={() => setIsChoiceModalOpen(true)}
        title="Create New Content"
      >
        ✏️
      </button>

      {/* Create Choice Modal */}
      <CreateChoiceModal
        isOpen={isChoiceModalOpen}
        onClose={() => setIsChoiceModalOpen(false)}
        onCreatePost={() => {
          setIsChoiceModalOpen(false);
          setIsPostModalOpen(true);
        }}
        onCreateReview={() => {
          setIsChoiceModalOpen(false);
          navigate('/books/review');
        }}
      />

      {/* Create Post Modal */}
      <CreatePostModal 
        isOpen={isPostModalOpen}
        onClose={() => setIsPostModalOpen(false)}
        onPostCreated={handlePostCreated}
      />

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
