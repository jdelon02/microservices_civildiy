import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ServiceDiscoveryPage from './pages/ServiceDiscoveryPage';
import HomePage from './pages/HomePage';
import PostDetailPage from './pages/PostDetailPage';
import UserProfilePage from './pages/UserProfilePage';
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
                <Link to="/profile" className="nav-link">👤 Profile</Link>
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
        <Route path="/profile" element={isAuthenticated ? <UserProfilePage /> : <LoginPage />} />
        <Route path="/posts/:postId" element={<PostDetailPage />} />
        <Route path="/posts/:postId/edit" element={isAuthenticated ? <PostDetailPage /> : <LoginPage />} />
        <Route path="/" element={<HomePage />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Router>
      <ThemeProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;
