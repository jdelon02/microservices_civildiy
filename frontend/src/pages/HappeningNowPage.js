import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { feedService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import FeedCard from '../components/FeedCard';
import './HappeningNowPage.css';

const HappeningNowPage = () => {
  const { isAuthenticated, token } = useAuth();
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [limit] = useState(50);
  const [skip, setSkip] = useState(0);

  useEffect(() => {
    const loadActivityStream = async () => {
      try {
        setLoading(true);
        const data = await feedService.getGlobal(token, limit, skip);
        setActivities(data.items || []);
      } catch (err) {
        setError(err.message || 'Failed to load activity stream');
      } finally {
        setLoading(false);
      }
    };

    loadActivityStream();
  }, [skip, limit, token]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getActivityIcon = (eventType) => {
    const icons = {
      'post_created': '📝',
      'post_updated': '✏️',
      'post_deleted': '🗑️',
      'comment_created': '💬',
      'user_followed': '👥',
      'profile_updated': '👤',
    };
    return icons[eventType] || '📌';
  };

  const getActivityLabel = (eventType) => {
    const labels = {
      'post_created': 'Created a post',
      'post_updated': 'Updated a post',
      'post_deleted': 'Deleted a post',
      'comment_created': 'Added a comment',
      'user_followed': 'Followed a user',
      'profile_updated': 'Updated their profile',
    };
    return labels[eventType] || eventType;
  };

  if (loading && activities.length === 0) {
    return <div className="happening-container"><p>Loading activity stream...</p></div>;
  }

  return (
    <main className="happening-container">
      <section className="happening-header">
        <h2>🔥 Happening Now</h2>
        <p>Live activity from the community</p>
      </section>

      {error && <div className="error-message">{error}</div>}

      {activities.length === 0 ? (
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
    </main>
  );
};

export default HappeningNowPage;
