import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import SearchableSelect from '../components/SearchableSelect'
import {
  ALL_COUNTRIES,
  MAJOR_CITIES,
  ALL_INDUSTRIES,
  ALL_DEGREE_TYPES,
  ALL_FIELDS_OF_STUDY,
} from '../data/comprehensiveData'

export default function OnboardingPage() {
  const navigate = useNavigate()
  const { register, login } = useAuth()
  const [step, setStep] = useState<'signin' | 'onboarding'>('signin')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)

  // Sign-in state
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [name, setName] = useState('')
  const [isNewUser, setIsNewUser] = useState(false)
  const [hasChosenMode, setHasChosenMode] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Onboarding state
  const [highestDegree, setHighestDegree] = useState('')
  const [majors, setMajors] = useState<string[]>([])
  const [graduationYear, setGraduationYear] = useState('')
  const [nationality, setNationality] = useState('')
  const [currentCountry, setCurrentCountry] = useState('')
  const [currentCity, setCurrentCity] = useState('')
  const [preferredIndustries, setPreferredIndustries] = useState<string[]>([])
  const [preferredCountries, setPreferredCountries] = useState<string[]>([])
  const [preferredCities, setPreferredCities] = useState<string[]>([])
  const [yearsExperience, setYearsExperience] = useState('')
  const [remotePreference, setRemotePreference] = useState('')
  const [workAuthorization, setWorkAuthorization] = useState('')
  const [jobTypePreference] = useState('Full-time')
  const [primaryRolePreference] = useState('')
  const [onboardingStep, setOnboardingStep] = useState<1 | 2>(1)

  const getPasswordStrength = () => {
    if (!password) return ''
    if (password.length < 6) return 'Password is very weak.'
    if (password.length < 8) return 'Password is weak. Consider adding more characters.'
    if (!/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
      return 'Password is okay. Add a mix of letters and numbers for better security.'
    }
    return 'Password looks strong.'
  }

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrors({})
    
    if (isNewUser) {
      // For new users, validate account fields then move to onboarding
      const newErrors: Record<string, string> = {}
      if (!name.trim()) newErrors.name = 'Full name is required.'
      if (!email.trim()) newErrors.email = 'Email address is required.'
      else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        newErrors.email = 'Please enter a valid email address.'
      }
      if (!password) newErrors.password = 'Password is required.'
      if (!confirmPassword) newErrors.confirmPassword = 'Please confirm your password.'
      else if (password !== confirmPassword) {
        newErrors.confirmPassword = 'Passwords do not match.'
      }

      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors)
        return
      }

      setStep('onboarding')
      setOnboardingStep(1)
      setErrors({})
      return
    }

    // For existing users, log in
    setLoading(true)
    try {
      console.log('Logging in existing user...', { email })
      await login(email, password)
      console.log('Login successful, waiting for user state to update...')
      
      // Wait a bit longer to ensure user state is fully updated
      await new Promise(resolve => setTimeout(resolve, 300))
      
      console.log('Navigating to homepage...')
      navigate('/')
    } catch (err: any) {
      console.error('Login error in OnboardingPage:', err)
      console.error('Full error object:', JSON.stringify(err, null, 2))
      const errorMsg = err.message || err.response?.data?.detail || 'Login failed. Please check your credentials.'
      setErrors({ general: errorMsg })
    } finally {
      setLoading(false)
    }
  }

  const handleCompleteOnboarding = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrors({})
    setLoading(true)

    try {
      // Validate required fields for step 1 (background)
      if (onboardingStep === 1) {
        const stepErrors: Record<string, string> = {}
        if (!highestDegree) stepErrors.highestDegree = 'Highest education level is required.'
        if (!majors.length) stepErrors.majors = 'Please add at least one field of study.'

        if (Object.keys(stepErrors).length > 0) {
          setErrors(stepErrors)
          setLoading(false)
          return
        }

        // Move to second preferences page (optional details)
        setOnboardingStep(2)
        setLoading(false)
        return
      }

      // Step 2 submit: actually create the account
      if (!email || !password || !name.trim()) {
        setErrors({ general: 'Please complete your account details on the previous step.' })
        setLoading(false)
        return
      }

      const profileData = {
        email,
        password,
        name: name.trim(),
        highest_degree: highestDegree || undefined,
        major: majors.length > 0 ? majors : undefined,
        graduation_year: graduationYear ? parseInt(graduationYear) : undefined,
        country: currentCountry || undefined,
        primary_industry_preference: preferredIndustries[0] || undefined,
        industry_preferences: preferredIndustries.length > 0 ? preferredIndustries : undefined,
        desired_countries: preferredCountries.length > 0 ? preferredCountries : undefined,
        remote_preference: remotePreference || undefined,
        work_authorization: workAuthorization || undefined,
        years_experience: yearsExperience ? parseInt(yearsExperience) : undefined,
        job_type_preference: jobTypePreference || undefined,
        primary_role_preference: primaryRolePreference || undefined,
      }
      
      console.log('Registering user with profile data...')
      await register(email, password, name, profileData)
      console.log('Registration successful. Prompting user to log in...')
      
      // Switch back to sign-in step with a success message
      setStep('signin')
      setIsNewUser(false)
      setErrors({ general: 'Account created successfully. Please sign in with your email and password.' })
    } catch (err: any) {
      console.error('Registration error:', err)
      setErrors({ general: err.message || 'Registration failed. Please try again.' })
    } finally {
      setLoading(false)
    }
  }

  if (step === 'signin') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Job Tracker</h1>
            <p className="text-gray-600">
              Track your applications and receive tailored job recommendations.
            </p>
          </div>

          {errors.general && (
            <div className="mb-4 rounded-md bg-red-50 border-2 border-red-300 p-4">
              <div className="flex items-center">
                <svg className="h-5 w-5 text-red-600 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="text-sm font-medium text-red-800">{errors.general}</div>
              </div>
            </div>
          )}

          {/* Entry point buttons (only visible, no fields yet) */}
          <div className="flex flex-col space-y-3 mb-6">
            <button
              type="button"
              onClick={() => {
                setIsNewUser(true)
                setHasChosenMode(true)
                setErrors({})
              }}
              className={`w-full py-3 px-4 rounded-xl text-sm font-semibold transition-all shadow-sm ${
                isNewUser && hasChosenMode
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
              }`}
            >
              I’m a new user
            </button>
            <button
              type="button"
              onClick={() => {
                setIsNewUser(false)
                setHasChosenMode(true)
                setErrors({})
              }}
              className={`w-full py-3 px-4 rounded-xl text-sm font-semibold transition-all shadow-sm ${
                !isNewUser && hasChosenMode
                  ? 'bg-gray-900 text-white shadow-md'
                  : 'bg-gray-50 text-gray-800 hover:bg-gray-100'
              }`}
            >
              Log in
            </button>
          </div>

          {hasChosenMode && (
          <form onSubmit={handleSignIn} className="space-y-6">
            {isNewUser && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Full name <span className="text-red-500 text-xs">(Required)</span>
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Clara Mouzannar"
                />
                {errors.name && (
                  <p className="mt-1 text-xs text-red-600">{errors.name}</p>
                )}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email address <span className="text-red-500 text-xs">(Required)</span>
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="name@example.com"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-600">{errors.email}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password <span className="text-red-500 text-xs">(Required)</span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent pr-12"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 px-3 text-xs text-gray-500 hover:text-gray-700"
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
              {isNewUser && (
                <p className="mt-1 text-xs text-gray-500">{getPasswordStrength()}</p>
              )}
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">{errors.password}</p>
              )}
            </div>

            {isNewUser && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm password <span className="text-red-500 text-xs">(Required)</span>
                </label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent pr-12"
                    placeholder="Re-enter your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((v) => !v)}
                    className="absolute inset-y-0 right-0 px-3 text-xs text-gray-500 hover:text-gray-700"
                  >
                    {showConfirmPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="mt-1 text-xs text-red-600">{errors.confirmPassword}</p>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors shadow-md"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {isNewUser ? 'Processing...' : 'Signing in...'}
                </span>
              ) : (
                isNewUser ? 'Create account' : 'Sign in'
              )}
            </button>
          </form>
          )}
        </div>
      </div>
    )
  }

  // Onboarding questions
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-white py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="mb-6 flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-1">Set your job preferences</h2>
              <p className="text-gray-600">
                This takes about 1 minute. You can edit these preferences anytime from your profile.
              </p>
            </div>
            <span className="text-xs font-medium text-indigo-600 mt-1">
              Step {onboardingStep} of 2
            </span>
          </div>

          {errors.general && (
            <div className="mb-4 rounded-md bg-red-50 border border-red-200 p-4">
              <div className="text-sm text-red-800">{errors.general}</div>
            </div>
          )}

          <form onSubmit={handleCompleteOnboarding} className="space-y-6">
            {/* Section A: Background (Required) */}
            {onboardingStep === 1 && (
              <>
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">
                    Background <span className="text-red-500 text-xs">(Required)</span>
                  </h3>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Highest education level
                  </label>
                  <SearchableSelect
                    options={ALL_DEGREE_TYPES}
                    selected={highestDegree ? [highestDegree] : []}
                    onChange={(selected) => setHighestDegree(selected[0] || '')}
                    placeholder="Search your highest education level"
                    multiple={false}
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Field of study / Major (you can select multiple)
                  </label>
                  <SearchableSelect
                    options={ALL_FIELDS_OF_STUDY}
                    selected={majors}
                    onChange={setMajors}
                    placeholder="Search and select your field(s) of study"
                    multiple={true}
                  />
                  {majors.length > 0 && (
                    <p className="mt-2 text-xs text-gray-500">Selected: {majors.join(', ')}</p>
                  )}
                </div>
              </>
            )}

            {onboardingStep === 2 && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Graduation year (Optional)
                  </label>
                  <input
                    type="number"
                    min="1950"
                    max="2030"
                    value={graduationYear}
                    onChange={(e) => setGraduationYear(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="2024"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Nationality (Optional)
                  </label>
                  <SearchableSelect
                    options={ALL_COUNTRIES}
                    selected={nationality ? [nationality] : []}
                    onChange={(selected) => setNationality(selected[0] || '')}
                    placeholder="Search your nationality"
                    multiple={false}
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Country you currently live in (Optional)
                  </label>
                  <SearchableSelect
                    options={ALL_COUNTRIES}
                    selected={currentCountry ? [currentCountry] : []}
                    onChange={(selected) => setCurrentCountry(selected[0] || '')}
                    placeholder="Search your current country"
                    multiple={false}
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    City you currently live in (Optional)
                  </label>
                  <SearchableSelect
                    options={MAJOR_CITIES}
                    selected={currentCity ? [currentCity] : []}
                    onChange={(selected) => setCurrentCity(selected[0] || '')}
                    placeholder="Search your current city"
                    multiple={false}
                  />
                </div>

                {/* Section B: What you want */}
                <div className="pt-2 border-t border-gray-100">
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">What you want</h3>
                  <p className="text-xs text-gray-500 mb-3">
                    These help us prioritize the right kind of roles for you.
                  </p>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Industries you are interested in (Optional)
                  </label>
                  <SearchableSelect
                    options={ALL_INDUSTRIES}
                    selected={preferredIndustries}
                    onChange={setPreferredIndustries}
                    placeholder="Search and select industries"
                    multiple={true}
                  />
                  {preferredIndustries.length > 0 && (
                    <p className="mt-2 text-xs text-gray-500">Selected: {preferredIndustries.join(', ')}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Countries you would like to work in (Optional)
                  </label>
                  <SearchableSelect
                    options={ALL_COUNTRIES}
                    selected={preferredCountries}
                    onChange={setPreferredCountries}
                    placeholder="Search and select countries"
                    multiple={true}
                  />
                  {preferredCountries.length > 0 && (
                    <p className="mt-2 text-xs text-gray-500">Selected: {preferredCountries.join(', ')}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Cities you would like to work in (Optional)
                  </label>
                  <SearchableSelect
                    options={MAJOR_CITIES}
                    selected={preferredCities}
                    onChange={setPreferredCities}
                    placeholder="Search and select cities"
                    multiple={true}
                  />
                  {preferredCities.length > 0 && (
                    <p className="mt-2 text-xs text-gray-500">Selected: {preferredCities.join(', ')}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Years of professional experience (Optional)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="50"
                    value={yearsExperience}
                    onChange={(e) => setYearsExperience(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="2"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Work location preference (Optional)
                  </label>
                  <select
                    value={remotePreference}
                    onChange={(e) => setRemotePreference(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select preference</option>
                    <option value="Remote">Remote</option>
                    <option value="On-site">On-site</option>
                    <option value="Hybrid">Hybrid</option>
                    <option value="Any">Any</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Work authorization status (Optional)
                  </label>
                  <select
                    value={workAuthorization}
                    onChange={(e) => setWorkAuthorization(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select status</option>
                    <option value="I can work without sponsorship">I can work without sponsorship</option>
                    <option value="I need sponsorship">I need sponsorship</option>
                    <option value="Not sure">Not sure</option>
                  </select>
                </div>
              </>
            )}

            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => {
                  if (onboardingStep === 2) {
                    setOnboardingStep(1)
                  } else {
                    setStep('signin')
                  }
                }}
                className="flex-1 py-3 px-4 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50"
              >
                {onboardingStep === 2 ? 'Back' : 'Cancel'}
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 py-3 px-4 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? 'Saving...' : onboardingStep === 1 ? 'Next' : 'Finish setup'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
