import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ServiceDiscoveryPage from './pages/ServiceDiscoveryPage';
import PostsPage from './pages/PostsPage';
import CreatePostPage from './pages/CreatePostPage';
import PostDetailPage from './pages/PostDetailPage';
import './App.css';

function AppContent() {
  const { isAuthenticated, user, logout, loading } = useAuth();

  if (loading) {
    return <div className="App"><p>Loading...</p></div>;
  }

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <Link to="/" className="logo">
            <h1>CivilDIY</h1>
          </Link>
          <nav className="nav">
            <Link to="/services" className="nav-link">Services</Link>
            {isAuthenticated ? (
              <>
                <span className="user-info">Welcome, {user?.email}</span>
                <button onClick={logout} className="logout-btn">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="nav-link">Login</Link>
                <Link to="/register" className="nav-link">Register</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/services" element={<ServiceDiscoveryPage />} />
        <Route path="/posts" element={isAuthenticated ? <PostsPage /> : <LoginPage />} />
        <Route path="/posts/new" element={isAuthenticated ? <CreatePostPage /> : <LoginPage />} />
        <Route path="/posts/:postId" element={<PostDetailPage />} />
        <Route path="/posts/:postId/edit" element={isAuthenticated ? <PostDetailPage /> : <LoginPage />} />
        <Route path="/" element={
          isAuthenticated ? (
            <main>
              <section className="dashboard">
                <h2>Welcome, {user?.email}</h2>
                <p>Welcome back! Here you can manage your posts and profile.</p>
                <Link to="/posts" className="dashboard-link">View All Posts →</Link>
                <Link to="/posts/new" className="dashboard-link dashboard-link-primary">Create New Post →</Link>
              </section>
            </main>
          ) : (
            <main>
              <section className="hero">
                <h2>Welcome to CivilDIY</h2>
                <p>Share your DIY projects, learn from others, and build together.</p>
                <Link to="/register" className="cta-button">Get Started</Link>
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
          )
        } />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;
