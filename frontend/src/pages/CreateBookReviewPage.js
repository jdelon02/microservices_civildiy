import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import BookReviewForm from '../components/BookReviewForm';
import './CreateBookReviewPage.css';

const CreateBookReviewPage = () => {
  const navigate = useNavigate();
  const { token, isAuthenticated } = useAuth();

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    navigate('/login');
    return null;
  }

  const handleCancel = () => {
    navigate('/');
  };

  const handleSuccess = () => {
    // Redirect to home page after successful submission
    navigate('/');
  };

  return (
    <main className="create-book-review-page">
      <BookReviewForm
        token={token}
        onSuccess={handleSuccess}
        onCancel={handleCancel}
      />
    </main>
  );
};

export default CreateBookReviewPage;
