import React from 'react';
import './CreateChoiceModal.css';

const CreateChoiceModal = ({ isOpen, onClose, onCreatePost, onCreateReview }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="choice-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          ✕
        </button>

        <h2>What would you like to create?</h2>
        <p className="subtitle">Choose an option to get started</p>

        <div className="choices-container">
          <button className="choice-button post-choice" onClick={onCreatePost}>
            <div className="choice-icon">📝</div>
            <div className="choice-title">Create a Post</div>
            <div className="choice-description">Share a DIY project or idea with the community</div>
          </button>

          <button className="choice-button review-choice" onClick={onCreateReview}>
            <div className="choice-icon">📚</div>
            <div className="choice-title">Review a Book</div>
            <div className="choice-description">Share your thoughts on a book you've read</div>
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreateChoiceModal;
