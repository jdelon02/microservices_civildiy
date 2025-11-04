import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const [theme, setThemeState] = useState('light');
  const [themePreference, setThemePreferenceState] = useState('system'); // 'light', 'dark', 'system'

  // Initialize theme from localStorage
  useEffect(() => {
    const savedPreference = localStorage.getItem('themePreference');
    if (savedPreference) {
      setThemePreferenceState(savedPreference);
    }
  }, []);

  // Apply theme based on preference
  useEffect(() => {
    let effectiveTheme = themePreference;

    if (themePreference === 'system') {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      effectiveTheme = prefersDark ? 'dark' : 'light';
    }

    setThemeState(effectiveTheme);
    document.documentElement.setAttribute('data-theme', effectiveTheme);
    localStorage.setItem('themePreference', themePreference);
  }, [themePreference]);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (themePreference === 'system') {
        const prefersDark = mediaQuery.matches;
        setThemeState(prefersDark ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [themePreference]);

  const setThemePreference = (preference) => {
    setThemePreferenceState(preference);
  };

  return (
    <ThemeContext.Provider value={{ theme, themePreference, setThemePreference }}>
      {children}
    </ThemeContext.Provider>
  );
};

export default ThemeContext;
