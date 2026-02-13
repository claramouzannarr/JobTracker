import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import HomePage from './pages/HomePage'
import OnboardingPage from './pages/OnboardingPage'
import { AuthProvider, useAuth } from './contexts/AuthContext'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading, token } = useAuth()

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>
  }

  // Allow access if user has a token, even if user object isn't loaded yet
  // This prevents redirect loops when token is valid but /auth/me fails temporarily
  const hasToken = token || localStorage.getItem('token')
  
  if (!user && !hasToken) {
    return <Navigate to="/onboarding" replace />
  }

  // If we have a token but no user, still allow access (user might load later)
  return <>{children}</>
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <HomePage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App

