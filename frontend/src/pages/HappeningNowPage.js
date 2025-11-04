import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { feedService } from '../services/api';
import './HappeningNowPage.css';

const HappeningNowPage = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [limit] = useState(50);
  const [skip, setSkip] = useState(0);

  useEffect(() => {
    const loadActivityStream = async () => {
      try {
        setLoading(true);
        const data = await feedService.getGlobal(limit, skip);
        setActivities(data.items || []);
      } catch (err) {
        setError(err.message || 'Failed to load activity stream');
      } finally {
        setLoading(false);
      }
    };

    loadActivityStream();
  }, [skip, limit]);

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
            <article key={`${activity.post_id}-${activity.timestamp}-${index}`} className="activity-card">
              <div className="activity-icon">
                {getActivityIcon(activity.event_type)}
              </div>

              <div className="activity-content">
                <div className="activity-main">
                  <p className="activity-label">
                    User {activity.user_id} {getActivityLabel(activity.event_type)}
                  </p>
                  {activity.title && (
                    <p className="activity-title">{activity.title}</p>
                  )}
                </div>

                <p className="activity-time">
                  {formatDate(activity.timestamp)}
                </p>
              </div>

              {activity.post_id && (
                <Link to={`/posts/${activity.post_id}`} className="activity-link">
                  View →
                </Link>
              )}
            </article>
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
