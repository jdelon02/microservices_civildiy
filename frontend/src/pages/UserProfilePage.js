import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { profileService } from '../services/api';
import './UserProfilePage.css';

const UserProfilePage = () => {
  const { token } = useAuth();
  const [profile, setProfile] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form state
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    dob: '',
    address: '',
    city: '',
    state: '',
    zip_code: '',
    country: '',
    phone: '',
    bio: '',
  });

  // Load profile on mount
  useEffect(() => {
    if (token) {
      loadProfile();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const loadProfile = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await profileService.get(token);
      setProfile(data);
      setFormData({
        first_name: data.first_name || '',
        last_name: data.last_name || '',
        dob: data.dob || '',
        address: data.address || '',
        city: data.city || '',
        state: data.state || '',
        zip_code: data.zip_code || '',
        country: data.country || '',
        phone: data.phone || '',
        bio: data.bio || '',
      });
      setIsEditing(false);
    } catch (err) {
      // Profile doesn't exist (404), allow creation
      const errorMsg = err.message || '';
      if (errorMsg.includes('404') || errorMsg.includes('not found')) {
        setProfile(null);
        setIsEditing(true);
        setError(''); // Clear error to show form
      } else {
        setProfile(null);
        setError(errorMsg || 'Failed to load profile');
        setIsEditing(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Basic validation
    if (!formData.first_name.trim() && !formData.last_name.trim()) {
      setError('Please provide at least a first or last name');
      return;
    }

    setSaving(true);

    try {
      let result;
      if (profile) {
        // Update existing profile
        result = await profileService.update(token, formData);
        setSuccess('Profile updated successfully!');
      } else {
        // Create new profile
        result = await profileService.create(token, formData);
        setSuccess('Profile created successfully!');
      }
      
      setProfile(result);
      setIsEditing(false);
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setError('');
  };

  const handleCancel = () => {
    setIsEditing(false);
    if (profile) {
      // Reset form to current profile data
      setFormData({
        first_name: profile.first_name || '',
        last_name: profile.last_name || '',
        dob: profile.dob || '',
        address: profile.address || '',
        city: profile.city || '',
        state: profile.state || '',
        zip_code: profile.zip_code || '',
        country: profile.country || '',
        phone: profile.phone || '',
        bio: profile.bio || '',
      });
    }
    setError('');
  };

  if (loading) {
    return <div className="profile-container"><p>Loading profile...</p></div>;
  }

  return (
    <main className="profile-container">
      <div className="profile-card">
        <h1>{profile ? 'My Profile' : 'Create Your Profile'}</h1>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        {isEditing ? (
          <form onSubmit={handleSubmit} className="profile-form">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="first_name">First Name</label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  value={formData.first_name}
                  onChange={handleInputChange}
                  placeholder="John"
                  disabled={saving}
                />
              </div>

              <div className="form-group">
                <label htmlFor="last_name">Last Name</label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  value={formData.last_name}
                  onChange={handleInputChange}
                  placeholder="Doe"
                  disabled={saving}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="dob">Date of Birth</label>
                <input
                  id="dob"
                  name="dob"
                  type="date"
                  value={formData.dob}
                  onChange={handleInputChange}
                  disabled={saving}
                />
              </div>

              <div className="form-group">
                <label htmlFor="phone">Phone</label>
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={handleInputChange}
                  placeholder="(555) 000-0000"
                  disabled={saving}
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="address">Address</label>
              <input
                id="address"
                name="address"
                type="text"
                value={formData.address}
                onChange={handleInputChange}
                placeholder="123 Main St"
                disabled={saving}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="city">City</label>
                <input
                  id="city"
                  name="city"
                  type="text"
                  value={formData.city}
                  onChange={handleInputChange}
                  placeholder="New York"
                  disabled={saving}
                />
              </div>

              <div className="form-group">
                <label htmlFor="state">State</label>
                <input
                  id="state"
                  name="state"
                  type="text"
                  value={formData.state}
                  onChange={handleInputChange}
                  placeholder="NY"
                  disabled={saving}
                />
              </div>

              <div className="form-group">
                <label htmlFor="zip_code">Zip Code</label>
                <input
                  id="zip_code"
                  name="zip_code"
                  type="text"
                  value={formData.zip_code}
                  onChange={handleInputChange}
                  placeholder="10001"
                  disabled={saving}
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="country">Country</label>
              <input
                id="country"
                name="country"
                type="text"
                value={formData.country}
                onChange={handleInputChange}
                placeholder="United States"
                disabled={saving}
              />
            </div>

            <div className="form-group">
              <label htmlFor="bio">Bio</label>
              <textarea
                id="bio"
                name="bio"
                value={formData.bio}
                onChange={handleInputChange}
                placeholder="Tell us about yourself..."
                rows={4}
                disabled={saving}
              />
            </div>

            <div className="form-actions">
              <button
                type="submit"
                disabled={saving}
                className="save-btn"
              >
                {saving ? 'Saving...' : 'Save Profile'}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                disabled={saving}
                className="cancel-btn"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : profile ? (
          <div className="profile-view">
            <div className="profile-section">
              <div className="info-row">
                <div className="info-group">
                  <label>First Name:</label>
                  <p>{profile.first_name || 'Not provided'}</p>
                </div>
                <div className="info-group">
                  <label>Last Name:</label>
                  <p>{profile.last_name || 'Not provided'}</p>
                </div>
              </div>

              <div className="info-row">
                <div className="info-group">
                  <label>Date of Birth:</label>
                  <p>{profile.dob || 'Not provided'}</p>
                </div>
                <div className="info-group">
                  <label>Phone:</label>
                  <p>{profile.phone || 'Not provided'}</p>
                </div>
              </div>

              <div className="info-group">
                <label>Address:</label>
                <p>{profile.address || 'Not provided'}</p>
              </div>

              <div className="info-row">
                <div className="info-group">
                  <label>City:</label>
                  <p>{profile.city || 'Not provided'}</p>
                </div>
                <div className="info-group">
                  <label>State:</label>
                  <p>{profile.state || 'Not provided'}</p>
                </div>
                <div className="info-group">
                  <label>Zip Code:</label>
                  <p>{profile.zip_code || 'Not provided'}</p>
                </div>
              </div>

              <div className="info-group">
                <label>Country:</label>
                <p>{profile.country || 'Not provided'}</p>
              </div>

              <div className="info-group">
                <label>Bio:</label>
                <p className="bio-text">{profile.bio || 'Not provided'}</p>
              </div>
            </div>

            <div className="profile-actions">
              <button onClick={handleEdit} className="edit-btn">
                Edit Profile
              </button>
            </div>
          </div>
        ) : (
          <div className="profile-view">
            <div className="profile-section">
              <p>Unable to load profile. Please try again.</p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
};

export default UserProfilePage;
