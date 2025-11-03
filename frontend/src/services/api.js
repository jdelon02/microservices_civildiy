const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

// Helper to get auth headers
const getHeaders = (token) => {
  const headers = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
};

// Generic fetch wrapper
const apiCall = async (endpoint, options = {}) => {
  const { token, method = 'GET', body = null, ...rest } = options;

  const url = `${API_BASE_URL}${endpoint}`;
  const fetchOptions = {
    method,
    headers: getHeaders(token),
    ...rest,
  };

  if (body) {
    fetchOptions.body = JSON.stringify(body);
  }

  const response = await fetch(url, fetchOptions);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
};

// Auth endpoints
export const authService = {
  register: (email, password) =>
    apiCall('/api/auth/register', {
      method: 'POST',
      body: { email, password },
    }),

  login: (email, password) =>
    apiCall('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    }),
};

// Posts endpoints
export const postsService = {
  create: (token, title, content, tags = []) =>
    apiCall('/api/posts', {
      token,
      method: 'POST',
      body: { title, content, tags },
    }),

  list: (token, userId = null, limit = 10, skip = 0) =>
    apiCall(`/api/posts?limit=${limit}&skip=${skip}${userId ? `&user_id=${userId}` : ''}`, {
      token,
    }),

  get: (postId) =>
    apiCall(`/api/posts/${postId}`),

  update: (token, postId, updates) =>
    apiCall(`/api/posts/${postId}`, {
      token,
      method: 'PUT',
      body: updates,
    }),

  delete: (token, postId) =>
    apiCall(`/api/posts/${postId}`, {
      token,
      method: 'DELETE',
    }),
};

// Activity feed endpoints
export const feedService = {
  getGlobal: (limit = 20, skip = 0) =>
    apiCall(`/api/activity-stream?limit=${limit}&skip=${skip}`),

  getUser: (token, limit = 20, skip = 0) =>
    apiCall(`/api/activity-stream/user?limit=${limit}&skip=${skip}`, {
      token,
    }),

  getStats: () =>
    apiCall('/api/activity-stream/stats'),
};

// User profile endpoints
export const profileService = {
  create: (token, profileData) =>
    apiCall('/api/profile', {
      token,
      method: 'POST',
      body: profileData,
    }),

  get: (token) =>
    apiCall('/api/profile', {
      token,
    }),

  update: (token, profileData) =>
    apiCall('/api/profile', {
      token,
      method: 'PUT',
      body: profileData,
    }),

  delete: (token) =>
    apiCall('/api/profile', {
      token,
      method: 'DELETE',
    }),
};
