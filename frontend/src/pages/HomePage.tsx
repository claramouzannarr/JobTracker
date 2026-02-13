import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'

interface Application {
  id: number
  company_name: string
  job_title: string
  job_url: string | null
  job_description_text: string | null
  industry: string | null
  country: string | null
  status: string
  stage_updated_at: string
  notes: string | null
  created_at: string
  resume_score: number | null
}

const STATUS_OPTIONS = ['Preparing', 'Applied', 'Interview Prep', 'Rejected']

export default function HomePage() {
  const { user, logout } = useAuth()
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [showResultsModal, setShowResultsModal] = useState(false)
  const [uploadingResume, setUploadingResume] = useState(false)
  const [evaluationResults, setEvaluationResults] = useState<any>(null)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})
  const [newApplication, setNewApplication] = useState({
    company_name: '',
    job_title: '',
    job_url: '',
    job_description_text: '',
    industry: '',
    country: '',
    status: 'Preparing',
    notes: '',
  })
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  useEffect(() => {
    // Only fetch applications if user is logged in
    if (user) {
      fetchApplications()
    } else {
      // Wait a bit for user to be set after login
      const timer = setTimeout(() => {
        if (user) {
          fetchApplications()
        } else {
          setLoading(false)
        }
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [user])

  const fetchApplications = async () => {
    try {
      // Ensure token is in headers
      const token = localStorage.getItem('token')
      if (!token) {
        setError('No authentication token found. Please log in.')
        setLoading(false)
        return
      }
      
      // Ensure axios defaults are set
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      
      const headers: any = {
        Authorization: `Bearer ${token}`
      }
      
      console.log('Fetching applications with token:', token.substring(0, 20) + '...')
      console.log('Token full length:', token.length)
      console.log('Axios defaults Authorization:', axios.defaults.headers.common['Authorization']?.substring(0, 50) + '...')
      console.log('Request headers being sent:', headers)
      
      // Use trailing slash to match backend route exactly
      const response = await axios.get('/applications/', { headers })
      console.log('Applications fetched:', response.data)
      setApplications(response.data)
      setError('') // Clear any previous errors
    } catch (err: any) {
      console.error('Error fetching applications:', err)
      console.error('Error response:', err.response)
      console.error('Error status:', err.response?.status)
      if (err.response?.status === 401) {
        setError('Authentication failed. Please log out and log back in.')
      } else {
        setError(err.response?.data?.detail || 'Failed to fetch applications')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleAddApplication = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setUploadingResume(true)
    
    // Resume is now mandatory
    if (!selectedFile) {
      setError('Resume upload is required. Please upload your resume before submitting.')
      setUploadingResume(false)
      return
    }
    
    try {
      // Ensure token is in headers
      const token = localStorage.getItem('token')
      if (!token) {
        setError('No authentication token found. Please log in.')
        setUploadingResume(false)
        return
      }
      
      // Ensure axios defaults are set
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      
      const headers: any = {
        Authorization: `Bearer ${token}`
      }
      
      console.log('Creating application with token:', token.substring(0, 20) + '...')
      console.log('Creating application...', newApplication)
      // Use trailing slash to match backend route exactly
      const response = await axios.post('/applications/', newApplication, { headers })
      const createdApp = response.data
      console.log('Application created:', createdApp)
      setApplications([...applications, createdApp])
      
      // Upload resume (mandatory)
      console.log('Uploading resume for application:', createdApp.id)
      await handleResumeUpload(createdApp.id)
    } catch (err: any) {
      console.error('Error creating application:', err)
      console.error('Error response:', err.response)
      setError(err.response?.data?.detail || err.message || 'Failed to create application. Please try again.')
      setUploadingResume(false)
    }
  }

  const handleResumeUpload = async (applicationId: number) => {
    if (!selectedFile) {
      setError('No file selected')
      setUploadingResume(false)
      return
    }
    
    setError('')
    try {
      console.log('Uploading resume file:', selectedFile.name)
      const formData = new FormData()
      formData.append('file', selectedFile)
      
      // Ensure token is in headers
      const token = localStorage.getItem('token')
      if (!token) {
        setError('No authentication token found. Please log in.')
        setUploadingResume(false)
        return
      }
      
      // Ensure axios defaults are set
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      
      const headers: any = {
        'Content-Type': 'multipart/form-data',
        Authorization: `Bearer ${token}`
      }
      
      console.log('Sending request to /resumes/upload/' + applicationId + ' with token:', token.substring(0, 20) + '...')
      const response = await axios.post(`/resumes/upload/${applicationId}`, formData, {
        headers,
        timeout: 120000, // 2 minute timeout for analysis
      })
      
      console.log('Resume upload response:', response.data)
      
      // Store evaluation results
      setEvaluationResults(response.data)
      
      // Close add modal and show results
      setShowAddModal(false)
      setShowResultsModal(true)
      resetForm()
      await fetchApplications() // Refresh to get updated scores
      setSuccess('Application created and resume analyzed successfully!')
    } catch (err: any) {
      console.error('Error uploading resume:', err)
      console.error('Error response:', err.response)
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to upload and analyze resume. Please try again.'
      setError(errorMsg)
      // Don't close modal on error so user can retry
      throw err // Re-throw so handleAddApplication knows it failed
    } finally {
      setUploadingResume(false)
      setSelectedFile(null)
    }
  }

  const resetForm = () => {
    setNewApplication({
      company_name: '',
      job_title: '',
      job_url: '',
      job_description_text: '',
      industry: '',
      country: '',
      status: 'Preparing',
      notes: '',
    })
    setSelectedFile(null)
  }

  const handleStatusChange = async (id: number, newStatus: string) => {
    try {
      const application = applications.find((app) => app.id === id)
      if (!application) return

      const response = await axios.put(`/applications/${id}`, {
        ...application,
        status: newStatus,
      })
      setApplications(applications.map((app) => (app.id === id ? response.data : app)))
      setSuccess('Status updated successfully!')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update status')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'Preparing': 'bg-gray-100 text-gray-800',
      'Applied': 'bg-blue-100 text-blue-800',
      'Interview Prep': 'bg-purple-100 text-purple-800',
      'Rejected': 'bg-red-100 text-red-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  const getScoreColor = (score: number | null) => {
    if (score === null) return 'text-gray-500'
    if (score >= 0.8) return 'text-green-600 font-semibold'
    if (score >= 0.6) return 'text-yellow-600 font-semibold'
    return 'text-red-600 font-semibold'
  }

  const formatScore = (score: number | null) => {
    if (score === null) return 'N/A'
    // Score is already 0-1 scale from backend
    return `${(score * 100).toFixed(0)}%`
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-lg text-gray-600">Loading applications...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with Profile */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Job Tracker</h1>
              <p className="text-sm text-gray-500 mt-1">Manage your job applications efficiently</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">{user?.name || 'User'}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
              <button
                onClick={() => setShowProfileModal(true)}
                className="px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-md hover:bg-indigo-100"
              >
                Edit Profile
              </button>
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-4 rounded-md bg-red-50 border border-red-200 p-4">
            <div className="text-sm text-red-800">{error}</div>
          </div>
        )}
        {success && (
          <div className="mb-4 rounded-md bg-green-50 border border-green-200 p-4">
            <div className="text-sm text-green-800">{success}</div>
          </div>
        )}

        {/* Add Application Button */}
        <div className="mb-6 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">My Applications</h2>
            <p className="text-sm text-gray-500 mt-1">
              {applications.length} {applications.length === 1 ? 'application' : 'applications'} tracked
            </p>
          </div>
          <button
            onClick={() => {
              setShowAddModal(true)
              setError('')
              setSuccess('')
            }}
            className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 shadow-sm font-medium"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Application
          </button>
        </div>

        {/* Applications Table */}
        <div className="bg-white shadow-sm rounded-lg overflow-hidden">
          {applications.length === 0 ? (
            <div className="p-12 text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No applications</h3>
              <p className="mt-1 text-sm text-gray-500">Get started by creating a new job application.</p>
              <div className="mt-6">
                <button
                  onClick={() => setShowAddModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  <svg className="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  New Application
                </button>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Company
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Role
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Industry
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Country
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Resume Score
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Applied Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {applications.map((app) => (
                    <tr key={app.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{app.company_name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{app.job_title}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{app.industry || '-'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{app.country || '-'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={`text-sm ${getScoreColor(app.resume_score)}`}>
                          {formatScore(app.resume_score)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <select
                          value={app.status}
                          onChange={(e) => handleStatusChange(app.id, e.target.value)}
                          className={`text-xs font-medium px-3 py-1.5 rounded-md border-0 ${getStatusColor(app.status)} focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer`}
                        >
                          {STATUS_OPTIONS.map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{formatDate(app.created_at)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex items-center gap-3">
                          {app.job_url && (
                            <a
                              href={app.job_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-indigo-600 hover:text-indigo-900"
                              title="View Job Description"
                            >
                              View JD
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Add Application Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <h3 className="text-xl font-semibold text-gray-900">New Job Application</h3>
              <button
                onClick={() => {
                  setShowAddModal(false)
                  resetForm()
                  setError('')
                }}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            <form onSubmit={handleAddApplication} className="p-6 space-y-4">
              {error && (
                <div className="mb-4 rounded-md bg-red-50 border-2 border-red-300 p-4">
                  <div className="flex items-center">
                    <svg className="h-5 w-5 text-red-600 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <div className="text-sm font-medium text-red-800">{error}</div>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Company Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={newApplication.company_name}
                    onChange={(e) =>
                      setNewApplication({ ...newApplication, company_name: e.target.value })
                    }
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Google"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Job Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={newApplication.job_title}
                    onChange={(e) =>
                      setNewApplication({ ...newApplication, job_title: e.target.value })
                    }
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Software Engineer"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Job Description URL (Optional)
                </label>
                <input
                  type="url"
                  value={newApplication.job_url}
                  onChange={(e) =>
                    setNewApplication({ ...newApplication, job_url: e.target.value })
                  }
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="https://company.com/jobs/123"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Job Description Text (Paste here if no URL)
                </label>
                <textarea
                  value={newApplication.job_description_text}
                  onChange={(e) =>
                    setNewApplication({ ...newApplication, job_description_text: e.target.value })
                  }
                  rows={6}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Paste the full job description here for better evaluation..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Industry
                  </label>
                  <input
                    type="text"
                    value={newApplication.industry}
                    onChange={(e) =>
                      setNewApplication({ ...newApplication, industry: e.target.value })
                    }
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Technology"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Country
                  </label>
                  <input
                    type="text"
                    value={newApplication.country}
                    onChange={(e) =>
                      setNewApplication({ ...newApplication, country: e.target.value })
                    }
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="United States"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Upload Resume (PDF, DOCX) <span className="text-red-500">* Required</span>
                </label>
                <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                  <div className="space-y-1 text-center">
                    <svg
                      className="mx-auto h-12 w-12 text-gray-400"
                      stroke="currentColor"
                      fill="none"
                      viewBox="0 0 48 48"
                    >
                      <path
                        d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                    <div className="flex text-sm text-gray-600">
                      <label className="relative cursor-pointer bg-white rounded-md font-medium text-indigo-600 hover:text-indigo-500">
                        <span>Upload a file</span>
                        <input
                          type="file"
                          className="sr-only"
                          accept=".pdf,.doc,.docx"
                          onChange={(e) => {
                            const file = e.target.files?.[0]
                            if (file) setSelectedFile(file)
                          }}
                        />
                      </label>
                      <p className="pl-1">or drag and drop</p>
                    </div>
                    <p className="text-xs text-gray-500">PDF, DOC, DOCX up to 10MB</p>
                    {selectedFile && (
                      <p className="text-sm text-indigo-600 mt-2">Selected: {selectedFile.name}</p>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes (Optional)
                </label>
                <textarea
                  value={newApplication.notes}
                  onChange={(e) =>
                    setNewApplication({ ...newApplication, notes: e.target.value })
                  }
                  rows={3}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Any additional notes about this application..."
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false)
                    resetForm()
                    setError('')
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadingResume || !selectedFile}
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploadingResume ? 'Analyzing Resume...' : 'Create Application & Analyze Resume'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Evaluation Results Modal */}
      {showResultsModal && evaluationResults && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <h3 className="text-2xl font-semibold text-gray-900">Resume Evaluation Results</h3>
              <button
                onClick={() => {
                  setShowResultsModal(false)
                  setEvaluationResults(null)
                }}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            <div className="p-6">
              {/* Overall Score */}
              <div className="mb-6 p-6 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border-2 border-indigo-200">
                <div className="text-center">
                  <div className="text-4xl font-bold text-indigo-600 mb-2">
                    {evaluationResults.overall_score?.toFixed(1) || 'N/A'}
                  </div>
                  <div className="text-lg text-gray-700">Overall Resume Score</div>
                  <div className="text-sm text-gray-500 mt-1">Out of 100 points</div>
                </div>
              </div>

              {/* Detailed Scores - Expandable Sections */}
              <div className="space-y-4">
                {/* Format Score */}
                <div className="border rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedSections({...expandedSections, format: !expandedSections.format})}
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="text-2xl font-bold text-gray-700">
                        {evaluationResults.evaluation_scores?.format?.score?.toFixed(1) || 'N/A'}
                      </div>
                      <div>
                        <h4 className="text-lg font-semibold text-gray-900">Format & Structure</h4>
                        <p className="text-sm text-gray-500">Sections, ordering, page count, bullet consistency</p>
                      </div>
                    </div>
                    <svg
                      className={`w-5 h-5 text-gray-500 transform transition-transform ${expandedSections.format ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {expandedSections.format && (
                    <div className="px-6 py-4 border-t bg-gray-50">
                      {/* Strengths */}
                      {evaluationResults.evaluation_scores?.format?.strengths?.length > 0 && (
                        <div className="mb-4">
                          <p className="text-sm font-semibold text-green-700 mb-2">✓ What's Working Well:</p>
                          <ul className="list-none space-y-1">
                            {evaluationResults.evaluation_scores.format.strengths.map((strength: string, idx: number) => (
                              <li key={idx} className="text-sm text-green-600">{strength}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Issues */}
                      {evaluationResults.evaluation_scores?.format?.issues?.length > 0 && (
                        <div className="mb-4">
                          <p className="text-sm font-semibold text-red-700 mb-2">⚠ Areas to Improve:</p>
                          <ul className="list-disc list-inside text-sm text-red-600 space-y-1">
                            {evaluationResults.evaluation_scores.format.issues.map((issue: string, idx: number) => (
                              <li key={idx}>{issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Detailed Breakdown */}
                      {evaluationResults.evaluation_scores?.format?.details && (
                        <div className="mt-4 space-y-3 text-sm">
                          {evaluationResults.evaluation_scores.format.details.sections && (
                            <div className="bg-white p-3 rounded border">
                              <p className="font-medium text-gray-700 mb-1">Sections Found:</p>
                              <p className="text-gray-600">{evaluationResults.evaluation_scores.format.details.sections.score_breakdown}</p>
                              {evaluationResults.evaluation_scores.format.details.sections.missing?.length > 0 && (
                                <p className="text-red-600 mt-1">Missing: {evaluationResults.evaluation_scores.format.details.sections.missing.join(', ')}</p>
                              )}
                            </div>
                          )}
                          
                          {evaluationResults.evaluation_scores.format.details.bullets && (
                            <div className="bg-white p-3 rounded border">
                              <p className="font-medium text-gray-700 mb-1">Bullet Points:</p>
                              <p className="text-gray-600">{evaluationResults.evaluation_scores.format.details.bullets.score_breakdown}</p>
                              {evaluationResults.evaluation_scores.format.details.bullets.total_bullets > 0 && (
                                <p className="text-gray-500 text-xs mt-1">
                                  {evaluationResults.evaluation_scores.format.details.bullets.total_experience_items} entries, 
                                  avg {evaluationResults.evaluation_scores.format.details.bullets.average_per_item} bullets each
                                </p>
                              )}
                            </div>
                          )}
                          
                          {evaluationResults.evaluation_scores.format.details.page_count && (
                            <div className="bg-white p-3 rounded border">
                              <p className="font-medium text-gray-700 mb-1">Page Count:</p>
                              <p className="text-gray-600">{evaluationResults.evaluation_scores.format.details.page_count.score_breakdown}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Job Compatibility */}
                {evaluationResults.evaluation_scores?.job_compatibility && (
                  <div className="border rounded-lg overflow-hidden">
                    <button
                      onClick={() => setExpandedSections({...expandedSections, job_compatibility: !expandedSections.job_compatibility})}
                      className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className="text-2xl font-bold text-gray-700">
                          {evaluationResults.evaluation_scores.job_compatibility.score?.toFixed(1) || 'N/A'}
                        </div>
                        <div>
                          <h4 className="text-lg font-semibold text-gray-900">Job Compatibility</h4>
                          <p className="text-sm text-gray-500">Keyword matching and semantic similarity</p>
                        </div>
                      </div>
                      <svg
                        className={`w-5 h-5 text-gray-500 transform transition-transform ${expandedSections.job_compatibility ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    
                    {expandedSections.job_compatibility && (
                      <div className="px-6 py-4 border-t bg-gray-50">
                        {evaluationResults.evaluation_scores.job_compatibility.matched_required?.length > 0 && (
                          <div className="mb-4">
                            <p className="text-sm font-semibold text-green-700 mb-2">✓ Matched Keywords ({evaluationResults.evaluation_scores.job_compatibility.matched_required.length}):</p>
                            <div className="flex flex-wrap gap-2">
                              {evaluationResults.evaluation_scores.job_compatibility.matched_required.map((keyword: string, idx: number) => (
                                <span key={idx} className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {evaluationResults.evaluation_scores.job_compatibility.missing_required?.length > 0 && (
                          <div className="mb-4">
                            <p className="text-sm font-semibold text-red-700 mb-2">⚠ Missing Keywords ({evaluationResults.evaluation_scores.job_compatibility.missing_required.length}):</p>
                            <div className="flex flex-wrap gap-2">
                              {evaluationResults.evaluation_scores.job_compatibility.missing_required.map((keyword: string, idx: number) => (
                                <span key={idx} className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">
                                  {keyword}
                                </span>
                              ))}
                            </div>
                            <p className="text-xs text-gray-600 mt-2">Consider adding these keywords to improve compatibility</p>
                          </div>
                        )}
                        
                        {evaluationResults.evaluation_scores.job_compatibility.soft_similarity && (
                          <div className="bg-white p-3 rounded border">
                            <p className="text-sm font-medium text-gray-700">Semantic Similarity: {(evaluationResults.evaluation_scores.job_compatibility.soft_similarity * 100).toFixed(1)}%</p>
                            <p className="text-xs text-gray-500 mt-1">Overall content similarity with job description</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Grammar Score */}
                <div className="border rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedSections({...expandedSections, grammar: !expandedSections.grammar})}
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="text-2xl font-bold text-gray-700">
                        {evaluationResults.evaluation_scores?.grammar?.score?.toFixed(1) || 'N/A'}
                      </div>
                      <div>
                        <h4 className="text-lg font-semibold text-gray-900">Grammar & Spelling</h4>
                        <p className="text-sm text-gray-500">
                          {evaluationResults.evaluation_scores?.grammar?.error_count || 0} errors found
                          {evaluationResults.evaluation_scores?.grammar?.errors_per_100_words && (
                            <span> ({evaluationResults.evaluation_scores.grammar.errors_per_100_words.toFixed(1)} per 100 words)</span>
                          )}
                        </p>
                      </div>
                    </div>
                    <svg
                      className={`w-5 h-5 text-gray-500 transform transition-transform ${expandedSections.grammar ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {expandedSections.grammar && (
                    <div className="px-6 py-4 border-t bg-gray-50">
                      {evaluationResults.evaluation_scores?.grammar?.error_count === 0 ? (
                        <div className="text-green-600 text-sm font-medium">✓ No grammar or spelling errors detected!</div>
                      ) : (
                        <>
                          {evaluationResults.evaluation_scores?.grammar?.top_examples?.length > 0 && (
                            <div>
                              <p className="text-sm font-semibold text-red-700 mb-2">Top Issues Found:</p>
                              <ul className="space-y-2">
                                {evaluationResults.evaluation_scores.grammar.top_examples.slice(0, 5).map((error: any, idx: number) => (
                                  <li key={idx} className="bg-white p-3 rounded border text-sm">
                                    <p className="font-medium text-gray-700">{error.issue}</p>
                                    <p className="text-gray-600 mt-1">"{error.text}"</p>
                                    {error.suggestion && (
                                      <p className="text-green-600 mt-1">→ Suggested: "{error.suggestion}"</p>
                                    )}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* ATS Score */}
                <div className="border rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedSections({...expandedSections, ats: !expandedSections.ats})}
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="text-2xl font-bold text-gray-700">
                        {evaluationResults.evaluation_scores?.ats?.score?.toFixed(1) || 'N/A'}
                      </div>
                      <div>
                        <h4 className="text-lg font-semibold text-gray-900">ATS Content Depth</h4>
                        <p className="text-sm text-gray-500">Action verbs, quantification, clichés, skills</p>
                      </div>
                    </div>
                    <svg
                      className={`w-5 h-5 text-gray-500 transform transition-transform ${expandedSections.ats ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {expandedSections.ats && (
                    <div className="px-6 py-4 border-t bg-gray-50 space-y-4">
                      {/* Strengths */}
                      {evaluationResults.evaluation_scores?.ats?.strengths?.length > 0 && (
                        <div>
                          <p className="text-sm font-semibold text-green-700 mb-2">✓ What's Working Well:</p>
                          <ul className="list-none space-y-1">
                            {evaluationResults.evaluation_scores.ats.strengths.map((strength: string, idx: number) => (
                              <li key={idx} className="text-sm text-green-600">{strength}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Issues */}
                      {evaluationResults.evaluation_scores?.ats?.issues?.length > 0 && (
                        <div>
                          <p className="text-sm font-semibold text-red-700 mb-2">⚠ Areas to Improve:</p>
                          <ul className="list-disc list-inside text-sm text-red-600 space-y-1">
                            {evaluationResults.evaluation_scores.ats.issues.map((issue: string, idx: number) => (
                              <li key={idx}>{issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Clichés */}
                      {evaluationResults.evaluation_scores?.ats?.cliches_found?.length > 0 && (
                        <div>
                          <p className="text-sm font-semibold text-yellow-700 mb-2">⚠ Clichés Found ({evaluationResults.evaluation_scores.ats.cliches_found.length}):</p>
                          <div className="flex flex-wrap gap-2">
                            {evaluationResults.evaluation_scores.ats.cliches_found.map((cliche: string, idx: number) => (
                              <span key={idx} className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">
                                {cliche}
                              </span>
                            ))}
                          </div>
                          <p className="text-xs text-gray-600 mt-2">Replace these with specific, measurable achievements</p>
                        </div>
                      )}
                      
                      {/* Detailed Breakdown */}
                      {evaluationResults.evaluation_scores?.ats?.details && (
                        <div className="mt-4 space-y-3 text-sm">
                          {evaluationResults.evaluation_scores.ats.details.action_verbs && (
                            <div className="bg-white p-3 rounded border">
                              <p className="font-medium text-gray-700 mb-1">Action Verbs:</p>
                              <p className="text-gray-600">{evaluationResults.evaluation_scores.ats.details.action_verbs.score_breakdown}</p>
                              {evaluationResults.evaluation_scores.ats.details.action_verbs.examples_strong?.length > 0 && (
                                <p className="text-green-600 text-xs mt-1">
                                  Strong verbs used: {evaluationResults.evaluation_scores.ats.details.action_verbs.examples_strong.join(', ')}
                                </p>
                              )}
                            </div>
                          )}
                          
                          {evaluationResults.evaluation_scores.ats.details.quantification && (
                            <div className="bg-white p-3 rounded border">
                              <p className="font-medium text-gray-700 mb-1">Quantification:</p>
                              <p className="text-gray-600">{evaluationResults.evaluation_scores.ats.details.quantification.score_breakdown}</p>
                              {evaluationResults.evaluation_scores.ats.details.quantification.bullets_with_numbers > 0 && (
                                <p className="text-gray-500 text-xs mt-1">
                                  {evaluationResults.evaluation_scores.ats.details.quantification.bullets_with_numbers} bullets with numbers
                                  {evaluationResults.evaluation_scores.ats.details.quantification.bullets_with_percentages > 0 && 
                                    `, ${evaluationResults.evaluation_scores.ats.details.quantification.bullets_with_percentages} with percentages`}
                                </p>
                              )}
                            </div>
                          )}
                          
                          {evaluationResults.evaluation_scores.ats.details.skills && (
                            <div className="bg-white p-3 rounded border">
                              <p className="font-medium text-gray-700 mb-1">Skills:</p>
                              <p className="text-gray-600">{evaluationResults.evaluation_scores.ats.details.skills.score_breakdown}</p>
                              {evaluationResults.evaluation_scores.ats.details.skills.missing_skills?.length > 0 && (
                                <p className="text-red-600 text-xs mt-1">
                                  Consider adding: {evaluationResults.evaluation_scores.ats.details.skills.missing_skills.slice(0, 5).join(', ')}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Suggestions */}
                {evaluationResults.suggestions && evaluationResults.suggestions.length > 0 && (
                  <div className="border rounded-lg p-4 bg-blue-50">
                    <h4 className="text-lg font-semibold text-gray-900 mb-3">Top Recommendations</h4>
                    <ol className="list-decimal list-inside text-sm text-gray-700 space-y-2">
                      {evaluationResults.suggestions.map((suggestion: string, idx: number) => (
                        <li key={idx}>{suggestion}</li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => {
                    setShowResultsModal(false)
                    setEvaluationResults(null)
                  }}
                  className="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Profile Modal - Placeholder for now */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">Edit Profile</h3>
              <button
                onClick={() => setShowProfileModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            <div className="p-6">
              <p className="text-gray-600">Profile editing feature coming soon!</p>
              <button
                onClick={() => setShowProfileModal(false)}
                className="mt-4 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
