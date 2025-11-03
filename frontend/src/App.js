import { AuthProvider } from './context/AuthContext';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <header className="App-header">
          <h1>CivilDIY</h1>
          <p>Community-driven construction and DIY project platform</p>
        </header>
        
        <main>
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
      </div>
    </AuthProvider>
  );
}

export default App;
