import React from 'react';
import DOMPurify from 'dompurify';

/**
 * Safe HTML Renderer Component
 * Renders HTML content safely by using DOMPurify to remove any malicious scripts
 */
const SafeHTMLRenderer = ({ html, className = '' }) => {
  if (!html) {
    return <p className={className}>No content available</p>;
  }

  // Sanitize the HTML on the frontend as well (defense in depth)
  const sanitizedHTML = DOMPurify.sanitize(html);

  return (
    <div
      className={`safe-html-content ${className}`}
      dangerouslySetInnerHTML={{ __html: sanitizedHTML }}
    />
  );
};

export default SafeHTMLRenderer;
