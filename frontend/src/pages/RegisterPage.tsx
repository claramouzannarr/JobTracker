import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import SearchableSelect from '../components/SearchableSelect'
import {
  COUNTRIES,
  FIELDS_OF_STUDY,
  DEGREE_OPTIONS,
  JOB_SECTORS,
  JOB_TYPES,
  REMOTE_OPTIONS,
  WORK_AUTHORIZATION_OPTIONS,
} from '../data/constants'

export default function RegisterPage() {
  const [step, setStep] = useState(1)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  // Basic info
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [name, setName] = useState('')
  const [age, setAge] = useState('')

  // Education
  const [highestDegree, setHighestDegree] = useState('')
  const [majors, setMajors] = useState<string[]>([])
  const [graduationYear, setGraduationYear] = useState('')

  // Preferences
  const [primaryRolePreference, setPrimaryRolePreference] = useState('')
  const [primaryIndustryPreference, setPrimaryIndustryPreference] = useState('')
  const [desiredCountries, setDesiredCountries] = useState<string[]>([])
  const [country, setCountry] = useState('')
  const [remotePreference, setRemotePreference] = useState('')
  const [workAuthorization, setWorkAuthorization] = useState('')
  const [yearsExperience, setYearsExperience] = useState('')
  const [jobTypePreference, setJobTypePreference] = useState('Full-time')

  const validateStep = (stepNum: number): boolean => {
    const newErrors: Record<string, string> = {}

    if (stepNum === 1) {
      if (!name.trim()) newErrors.name = 'Name is required'
      if (!email.trim()) {
        newErrors.email = 'Email is required'
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        newErrors.email = 'Please enter a valid email address'
      }
      if (!password) {
        newErrors.password = 'Password is required'
      } else if (password.length < 6) {
        newErrors.password = 'Password must be at least 6 characters'
      } else if (new TextEncoder().encode(password).length > 72) {
        newErrors.password = 'Password is too long. Please use 72 characters or less.'
      }
      if (password !== confirmPassword) {
        newErrors.confirmPassword = 'Passwords do not match'
      }
      if (age && (parseInt(age) < 16 || parseInt(age) > 100)) {
        newErrors.age = 'Age must be between 16 and 100'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (step < 3) {
      if (validateStep(step)) {
        setStep(step + 1)
        setErrors({})
      }
      return
    }

    // Final validation
    if (!validateStep(1)) {
      setStep(1)
      return
    }

    setErrors({})
    setLoading(true)

    try {
      const profileData = {
        email,
        password,
        name: name.trim(),
        age: age ? parseInt(age) : undefined,
        highest_degree: highestDegree || undefined,
        major: majors.length > 0 ? majors : undefined,
        graduation_year: graduationYear ? parseInt(graduationYear) : undefined,
        primary_role_preference: primaryRolePreference || undefined,
        primary_industry_preference: primaryIndustryPreference || undefined,
        desired_countries: desiredCountries.length > 0 ? desiredCountries : undefined,
        country: country || undefined,
        remote_preference: remotePreference || undefined,
        work_authorization: workAuthorization || undefined,
        years_experience: yearsExperience ? parseInt(yearsExperience) : undefined,
        job_type_preference: jobTypePreference || undefined,
      }

      console.log('Submitting registration with profile data:', {
        ...profileData,
        password: '***',
        majors: majors,
      })

      await register(email, password, name, profileData)
      navigate('/')
    } catch (err: any) {
      console.error('Registration error in RegisterPage:', err)
      console.error('Error message:', err.message)
      console.error('Error response:', err.response)
      
      let errorMessage = 'Registration failed'
      
      // Check if it's a validation error from FastAPI (array format)
      if (err.response?.data?.detail && Array.isArray(err.response.data.detail)) {
        const validationErrors: Record<string, string> = {}
        err.response.data.detail.forEach((error: any) => {
          if (error.loc && error.loc.length > 1) {
            const field = error.loc[error.loc.length - 1]
            validationErrors[field] = error.msg
          }
        })
        setErrors(validationErrors)
        
        // Navigate to the step with the error
        if (validationErrors.email || validationErrors.password || validationErrors.name) {
          setStep(1)
        } else if (validationErrors.major || validationErrors.highest_degree) {
          setStep(2)
        } else {
          setStep(3)
        }
        return
      }
      
      // Handle string error messages
      if (err.message) {
        errorMessage = err.message
      } else if (err.response?.data?.detail) {
        errorMessage = typeof err.response.data.detail === 'string' 
          ? err.response.data.detail 
          : JSON.stringify(err.response.data.detail)
      }
      
      setErrors({ general: errorMessage })
    } finally {
      setLoading(false)
    }
  }

  const renderStep1 = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Account Information</h3>
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
          Full Name *
        </label>
        <input
          id="name"
          name="name"
          type="text"
          required
          className={`appearance-none relative block w-full px-3 py-2 border ${
            errors.name ? 'border-red-300' : 'border-gray-300'
          } placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
          placeholder="John Doe"
          value={name}
          onChange={(e) => {
            setName(e.target.value)
            if (errors.name) setErrors({ ...errors, name: '' })
          }}
        />
        {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
      </div>
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
          Email Address *
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          className={`appearance-none relative block w-full px-3 py-2 border ${
            errors.email ? 'border-red-300' : 'border-gray-300'
          } placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
          placeholder="john.doe@example.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value)
            if (errors.email) setErrors({ ...errors, email: '' })
          }}
        />
        {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email}</p>}
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
          Password *
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={6}
          className={`appearance-none relative block w-full px-3 py-2 border ${
            errors.password ? 'border-red-300' : 'border-gray-300'
          } placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
          placeholder="Minimum 6 characters"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value)
            if (errors.password) setErrors({ ...errors, password: '' })
          }}
        />
        {errors.password && <p className="mt-1 text-sm text-red-600">{errors.password}</p>}
      </div>
      <div>
        <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
          Confirm Password *
        </label>
        <input
          id="confirmPassword"
          name="confirmPassword"
          type="password"
          autoComplete="new-password"
          required
          className={`appearance-none relative block w-full px-3 py-2 border ${
            errors.confirmPassword ? 'border-red-300' : 'border-gray-300'
          } placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
          placeholder="Confirm your password"
          value={confirmPassword}
          onChange={(e) => {
            setConfirmPassword(e.target.value)
            if (errors.confirmPassword) setErrors({ ...errors, confirmPassword: '' })
          }}
        />
        {errors.confirmPassword && <p className="mt-1 text-sm text-red-600">{errors.confirmPassword}</p>}
      </div>
      <div>
        <label htmlFor="age" className="block text-sm font-medium text-gray-700 mb-1">
          Age (Optional)
        </label>
        <input
          id="age"
          name="age"
          type="number"
          min="16"
          max="100"
          className={`appearance-none relative block w-full px-3 py-2 border ${
            errors.age ? 'border-red-300' : 'border-gray-300'
          } placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
          placeholder="25"
          value={age}
          onChange={(e) => {
            setAge(e.target.value)
            if (errors.age) setErrors({ ...errors, age: '' })
          }}
        />
        {errors.age && <p className="mt-1 text-sm text-red-600">{errors.age}</p>}
      </div>
    </div>
  )

  const renderStep2 = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Education & Experience</h3>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Highest Degree
        </label>
        <select
          className="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          value={highestDegree}
          onChange={(e) => setHighestDegree(e.target.value)}
        >
          <option value="">Select degree</option>
          {DEGREE_OPTIONS.map(deg => (
            <option key={deg} value={deg}>{deg}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Field(s) of Study (Select multiple)
        </label>
        <SearchableSelect
          options={FIELDS_OF_STUDY}
          selected={majors}
          onChange={setMajors}
          placeholder="Search and select fields of study (e.g., type 'M' for Mathematics, 'C' for Computer Science)"
          multiple={true}
        />
        {majors.length > 0 && (
          <p className="mt-1 text-xs text-gray-500">
            Selected: {majors.join(', ')}
          </p>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Graduation Year
          </label>
          <input
            type="number"
            min="1950"
            max="2030"
            className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            placeholder="2024"
            value={graduationYear}
            onChange={(e) => setGraduationYear(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Years of Professional Experience
          </label>
          <input
            type="number"
            min="0"
            max="50"
            className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            placeholder="2"
            value={yearsExperience}
            onChange={(e) => setYearsExperience(e.target.value)}
          />
        </div>
      </div>
    </div>
  )

  const renderStep3 = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Job Preferences</h3>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Preferred Job Role
        </label>
        <select
          className="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          value={primaryRolePreference}
          onChange={(e) => setPrimaryRolePreference(e.target.value)}
        >
          <option value="">Select role</option>
          {JOB_TYPES.map(role => (
            <option key={role} value={role}>{role}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Preferred Industry Sector
        </label>
        <select
          className="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          value={primaryIndustryPreference}
          onChange={(e) => setPrimaryIndustryPreference(e.target.value)}
        >
          <option value="">Select industry</option>
          {JOB_SECTORS.map(sector => (
            <option key={sector} value={sector}>{sector}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Current Country
        </label>
        <SearchableSelect
          options={COUNTRIES}
          selected={country ? [country] : []}
          onChange={(selected) => setCountry(selected[0] || '')}
          placeholder="Search country (e.g., type 'M' for Madrid, Spain)"
          multiple={false}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Preferred Job Locations (Select multiple)
        </label>
        <SearchableSelect
          options={COUNTRIES}
          selected={desiredCountries}
          onChange={setDesiredCountries}
          placeholder="Search and select countries (e.g., type 'U' for United States)"
          multiple={true}
        />
        {desiredCountries.length > 0 && (
          <p className="mt-1 text-xs text-gray-500">
            Selected: {desiredCountries.join(', ')}
          </p>
        )}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Work Location Preference
        </label>
        <select
          className="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          value={remotePreference}
          onChange={(e) => setRemotePreference(e.target.value)}
        >
          <option value="">Select preference</option>
          {REMOTE_OPTIONS.map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Work Authorization Status
        </label>
        <select
          className="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          value={workAuthorization}
          onChange={(e) => setWorkAuthorization(e.target.value)}
        >
          <option value="">Select status</option>
          {WORK_AUTHORIZATION_OPTIONS.map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Job Type Preference
        </label>
        <select
          className="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          value={jobTypePreference}
          onChange={(e) => setJobTypePreference(e.target.value)}
        >
          <option value="Full-time">Full-time</option>
          <option value="Part-time">Part-time</option>
          <option value="Internship">Internship</option>
          <option value="Contract">Contract</option>
        </select>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 to-white py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl w-full">
        <div className="bg-white shadow-xl rounded-lg p-8">
          <div className="mb-6">
            <h2 className="text-3xl font-extrabold text-gray-900 text-center">
              Create Your Account
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              Step {step} of 3: {step === 1 ? 'Account Information' : step === 2 ? 'Education & Experience' : 'Job Preferences'}
            </p>
            <div className="mt-4 w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(step / 3) * 100}%` }}
              />
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {errors.general && (
              <div className="rounded-md bg-red-50 border border-red-200 p-4">
                <div className="text-sm text-red-800">{errors.general}</div>
              </div>
            )}

            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}

            <div className="flex justify-between">
              {step > 1 && (
                <button
                  type="button"
                  onClick={() => {
                    setStep(step - 1)
                    setErrors({})
                  }}
                  className="px-6 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Previous
                </button>
              )}
              <div className={step > 1 ? "ml-auto" : "ml-auto w-full"}>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                >
                  {loading
                    ? 'Creating account...'
                    : step === 3
                    ? 'Create Account'
                    : 'Next'}
                </button>
              </div>
            </div>

            <div className="text-center">
              <Link
                to="/login"
                className="font-medium text-indigo-600 hover:text-indigo-500 text-sm"
              >
                Already have an account? Sign in
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
