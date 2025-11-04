import React from 'react';
import { Link } from 'react-router-dom';
import SafeHTMLRenderer from './SafeHTMLRenderer';
import './FeedCard.css';

const FeedCard = ({ activity, formatDate, onDelete }) => {
  const isPostEvent = activity.event_type.startsWith('post_');

  const getEventEmoji = () => {
    switch (activity.event_type) {
      case 'post.created':
        return '✍️';
      case 'post.updated':
        return '✏️';
      case 'post.deleted':
        return '🗑️';
      default:
        return '📌';
    }
  };

  const getEventText = () => {
    switch (activity.event_type) {
      case 'post.created':
        return 'posted';
      case 'post.updated':
        return 'updated a post';
      case 'post.deleted':
        return 'deleted a post';
      default:
        return 'posted';
    }
  };

  return (
    <article className="feed-card">
      {/* Header with avatar, username, and timestamp */}
      <div className="feed-card-header">
        <div className="feed-card-avatar">
          <div className="avatar-placeholder">
            {activity.username ? activity.username.charAt(0).toUpperCase() : 'U'}
          </div>
        </div>
        <div className="feed-card-info">
          <div className="feed-card-user">
            <span className="username">{activity.username || `User ${activity.user_id}`}</span>
            <span className="event-action">{getEventText()}</span>
          </div>
          <time className="feed-card-time">{formatDate(activity.timestamp)}</time>
        </div>
        {isPostEvent && activity.event_type === 'post.created' && (
          <span className="event-emoji">{getEventEmoji()}</span>
        )}
      </div>

      {/* Post content preview */}
      {activity.content && (
        <div className="feed-card-content">
          {/* Title */}
          {activity.title && (
            <div className="feed-post-title">
              <SafeHTMLRenderer html={activity.title} className="title-text" />
            </div>
          )}

          {/* Content preview with full HTML rendering */}
          <div className="feed-post-excerpt">
            <SafeHTMLRenderer html={activity.content} className="excerpt-text" />
          </div>
        </div>
      )}

      {/* Footer with interaction buttons */}
      {activity.post_id && (
        <div className="feed-card-footer">
          <Link to={`/posts/${activity.post_id}`} className="feed-card-link">
            View Full Post →
          </Link>
        </div>
      )}
    </article>
  );
};

export default FeedCard;
