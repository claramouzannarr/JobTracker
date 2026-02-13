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

  // Add axios interceptor to ensure token is always sent
  useEffect(() => {
    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        const storedToken = localStorage.getItem('token')
        console.log('Axios interceptor: Request to', config.url)
        console.log('Axios interceptor: Token available?', !!storedToken)
        if (storedToken && config.headers) {
          config.headers.Authorization = `Bearer ${storedToken}`
          console.log('Axios interceptor: Authorization header set:', config.headers.Authorization.substring(0, 50) + '...')
        } else {
          console.warn('Axios interceptor: No token found in localStorage!')
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    return () => {
      axios.interceptors.request.eject(requestInterceptor)
    }
  }, [])

  useEffect(() => {
    // Check for stored token
    const storedToken = localStorage.getItem('token')
    if (storedToken) {
      console.log('Restoring token from localStorage')
      setToken(storedToken)
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
      // Try to fetch user, but don't block if it fails
      fetchUser(storedToken).catch((err) => {
        console.log('Could not fetch user on load, but keeping token:', err)
        // Don't clear token on initial load failure - might be network issue
        // User can still try to use the app
      })
    } else {
      console.log('No token found in localStorage')
      setLoading(false)
    }
  }, [])

  const fetchUser = async (authToken: string) => {
    try {
      console.log('Fetching user data with token...')
      // Ensure token is set in axios defaults
      axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`
      
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
      console.error('Status code:', error.response?.status)
      
      // Don't automatically clear token - let user try to use the app
      // Only clear if explicitly 401 and we're sure token is invalid
      // This prevents clearing valid tokens due to network issues
      // Only clear token if it's a clear 401 authentication error
      // Don't clear on network errors or other issues
      if (error.response?.status === 401) {
        const errorDetail = error.response?.data?.detail || ''
        if (errorDetail.includes('Could not validate credentials') || 
            errorDetail.includes('Not authenticated') ||
            errorDetail.includes('Invalid token')) {
          console.log('Token invalid (401 auth error), clearing...')
          localStorage.removeItem('token')
          setToken(null)
          setUser(null)
          delete axios.defaults.headers.common['Authorization']
        } else {
          console.log('401 but unclear if token is invalid, keeping token')
        }
      } else {
        // For other errors (network, 500, etc.), keep the token and let user continue
        console.log('Non-auth error, keeping token')
      }
      // Don't throw error - let the app continue even if user fetch fails
      // The user might still be able to use the app with the token
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
      // Set token in state and localStorage FIRST
      setToken(access_token)
      localStorage.setItem('token', access_token)
      
      // Set axios defaults IMMEDIATELY
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      console.log('Axios Authorization header set:', axios.defaults.headers.common['Authorization'])

      // Use user info from login response (backend always returns it)
      if (userFromResponse) {
        console.log('Setting user from login response:', userFromResponse)
        setUser(userFromResponse)
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
            console.warn('No user data returned from /auth/me')
          }
        } catch (fetchError: any) {
          console.error('Failed to fetch user via /auth/me:', fetchError)
          // Don't fail login if we have a token - user can still use the app
          // Just log the error
        }
      }
      
      setLoading(false)
      console.log('Login process complete')
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

