import React, { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE_URL = '/api'

interface User {
  id: number
  email: string
  name: string | null
  // Add other user fields as needed
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name?: string, profileData?: any) => Promise<void>
  logout: () => void
  token: string | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState<string | null>(null)

  // Configure axios defaults
  axios.defaults.baseURL = API_BASE_URL

  useEffect(() => {
    // Check for stored token
    const storedToken = localStorage.getItem('token')
    if (storedToken) {
      setToken(storedToken)
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
      fetchUser(storedToken)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchUser = async (authToken: string) => {
    try {
      console.log('Fetching user data with token...')
      const response = await axios.get('/auth/me', {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      console.log('User data received:', response.data)
      const userData = response.data
      setUser(userData)
      console.log('User state updated successfully:', userData)
      return userData
    } catch (error: any) {
      console.error('Failed to fetch user:', error)
      console.error('Error details:', error.response?.data)
      // Clear invalid token
      localStorage.removeItem('token')
      setToken(null)
      setUser(null)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    try {
      setLoading(true)
      console.log('Attempting login for:', email)
      const response = await axios.post('/auth/login', { email, password })
      console.log('Login response received:', response.data)
      
      const { access_token, user: userFromResponse } = response.data
      if (!access_token) {
        throw new Error('No access token received from server')
      }
      
      console.log('Saving token to localStorage...')
      setToken(access_token)
      localStorage.setItem('token', access_token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      // Use user info from login response (backend always returns it)
      if (userFromResponse) {
        console.log('Setting user from login response:', userFromResponse)
        setUser(userFromResponse)
        setLoading(false)
        console.log('Login complete, user data loaded')
      } else {
        // Fallback: if somehow user is missing, try /auth/me
        console.warn('No user in login response, fetching via /auth/me...')
        try {
          const userData = await fetchUser(access_token)
          if (userData) {
            setUser(userData)
            console.log('User state set from /auth/me:', userData)
          } else {
            throw new Error('Failed to fetch user data after login')
          }
        } catch (fetchError: any) {
          console.error('Failed to fetch user via /auth/me:', fetchError)
          // Don't fail login if we have a token - user can still use the app
          // Just log the error
          setLoading(false)
        }
      }
    } catch (error: any) {
      console.error('Login error:', error)
      console.error('Error response:', error.response?.data)
      setLoading(false)
      const errorMessage = error.response?.data?.detail || error.message || 'Login failed. Please check your credentials.'
      throw new Error(errorMessage)
    }
  }

  const register = async (email: string, password: string, name?: string, profileData?: any) => {
    try {
      const registrationData = {
        email,
        password,
        name,
        ...profileData,
      }
      console.log('Registering with data:', { ...registrationData, password: '***' })
      const response = await axios.post('/auth/register', registrationData)
      console.log('Registration successful:', response.data)
      // Registration only - user will log in manually after this
      console.log('Registration complete. User should now log in manually.')
    } catch (error: any) {
      console.error('Registration error:', error)
      console.error('Error response:', error.response)
      
      // Handle validation errors
      if (error.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
          // FastAPI validation errors
          const errorMessages = error.response.data.detail.map((err: any) => {
            const field = err.loc ? err.loc[err.loc.length - 1] : 'field'
            return `${field}: ${err.msg}`
          }).join(', ')
          throw new Error(errorMessages)
        } else if (typeof error.response.data.detail === 'string') {
          throw new Error(error.response.data.detail)
        }
      }
      
      throw new Error(error.message || 'Registration failed. Please check your input and try again.')
    }
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('token')
    delete axios.defaults.headers.common['Authorization']
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

