import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import SearchableSelect from '../components/SearchableSelect'
import {
  ALL_COUNTRIES,
  ALL_INDUSTRIES,
  ALL_DEGREE_TYPES,
  ALL_FIELDS_OF_STUDY,
} from '../data/comprehensiveData'

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

interface JobRecommendation {
  job_id: number
  title: string
  company: string
  location_display?: string | null
  url?: string | null
  created_at?: string | null
  remote_type?: string | null
  salary_min?: number | null
  salary_max?: number | null
  description_text?: string | null
  score: number
}

// Interview prep (generated package)
interface PrepQuestion {
  id: string
  type: string
  question: string
  what_good_looks_like?: string[]
  common_mistakes?: string[]
  follow_ups?: string[]
  difficulty?: string
  evidence_from_docs?: string[]
}
interface PrepRoleContext {
  target_title?: string
  seniority?: string
  company?: string | null
  key_requirements?: string[]
}
interface PrepGeneratedJson {
  role_context?: PrepRoleContext
  questions?: PrepQuestion[]
  skill_gaps?: { matched?: string[]; missing?: string[]; priority_to_learn?: string[] }
  study_plan?: { day: number; focus: string; tasks: string[]; deliverable: string }[]
  answer_rubric?: { scoring_scale?: string; criteria?: { name: string; description: string }[] }
}
interface InterviewPrepRecord {
  id: number
  application_id: number
  questions: string[]
  resources_links: string[]
  topics_to_review: string[]
  generated_json: PrepGeneratedJson | null
  created_at: string
}

const STATUS_OPTIONS = ['Preparing', 'Applied', 'Interview Prep', 'Rejected']

export default function HomePage() {
  const { user, logout } = useAuth()
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showRecommendationsModal, setShowRecommendationsModal] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showNewApplicationChoice, setShowNewApplicationChoice] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [showResultsModal, setShowResultsModal] = useState(false)
  const [showApplicationDetailModal, setShowApplicationDetailModal] = useState(false)
  const [applicationDetailData, setApplicationDetailData] = useState<{
    application: Application
    evaluation_scores: any
    overall_score: number | null
    suggestions: string[]
  } | null>(null)
  const [detailExpandedSections, setDetailExpandedSections] = useState<Record<string, boolean>>({})
  const [reUploadFile, setReUploadFile] = useState<File | null>(null)
  const [reUploading, setReUploading] = useState(false)
  const [uploadingResume, setUploadingResume] = useState(false)
  const [evaluationResults, setEvaluationResults] = useState<any>(null)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})
  const [recommendations, setRecommendations] = useState<JobRecommendation[]>([])
  const [loadingRecommendations, setLoadingRecommendations] = useState(false)
  const [recommendationsError, setRecommendationsError] = useState('')
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
  const [profileForm, setProfileForm] = useState<Record<string, any>>({})
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileError, setProfileError] = useState('')

  // Interview prep
  const [showInterviewPrepModal, setShowInterviewPrepModal] = useState(false)
  const [interviewPrepAppId, setInterviewPrepAppId] = useState<number | null>(null)
  const [interviewPrepData, setInterviewPrepData] = useState<InterviewPrepRecord | null>(null)
  const [interviewPrepLoading, setInterviewPrepLoading] = useState(false)
  const [interviewPrepError, setInterviewPrepError] = useState('')
  const [generatingPrep, setGeneratingPrep] = useState(false)
  const [generateForm, setGenerateForm] = useState({ days: 7, focus: ['technical', 'behavioral'] as string[], difficulty: 'mixed' })
  const [practiceQuestionId, setPracticeQuestionId] = useState<string | null>(null)
  const [practiceAnswerText, setPracticeAnswerText] = useState('')
  const [evaluationResult, setEvaluationResult] = useState<{ score: number; strengths: string[]; missing_points: string[]; improved_answer: string; next_drill: string } | null>(null)
  const [evaluateLoading, setEvaluateLoading] = useState(false)
  const [voiceRecording, setVoiceRecording] = useState(false)
  const [voiceChunks, setVoiceChunks] = useState<Blob[]>([])
  const [voiceMediaRecorder, setVoiceMediaRecorder] = useState<MediaRecorder | null>(null)

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

  const openRecommendationsModal = async () => {
    setShowRecommendationsModal(true)
    setShowAddModal(false)
    setRecommendations([])
    setRecommendationsError('')
    setLoadingRecommendations(true)

    try {
      const token = localStorage.getItem('token')
      if (!token) {
        setRecommendationsError('No authentication token found. Please log in.')
        return
      }

      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      const headers: any = {
        Authorization: `Bearer ${token}`,
      }

      const response = await axios.get('/jobs/recommendations?limit=20', { headers })
      setRecommendations(response.data)
    } catch (err: any) {
      console.error('Error fetching job recommendations:', err)
      const message =
        err.response?.data?.detail ||
        err.message ||
        'Failed to load job recommendations. You can still add an application manually.'
      setRecommendationsError(message)
    } finally {
      setLoadingRecommendations(false)
    }
  }

  const handleUseRecommendation = (job: JobRecommendation) => {
    setNewApplication({
      company_name: job.company || '',
      job_title: job.title || '',
      job_url: job.url || '',
      job_description_text: job.description_text || '',
      industry: newApplication.industry,
      country: newApplication.country,
      status: 'Preparing',
      notes: newApplication.notes,
    })
    setShowRecommendationsModal(false)
    setError('')
    setSuccess('')
    setShowAddModal(true)
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

  const openApplicationDetail = async (appId: number) => {
    setShowApplicationDetailModal(true)
    setApplicationDetailData(null)
    setDetailExpandedSections({})
    setReUploadFile(null)
    setError('')
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      const res = await axios.get(`/applications/${appId}/evaluation`)
      setApplicationDetailData(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load application details')
    }
  }

  const handleReUploadResume = async (applicationId: number) => {
    if (!reUploadFile) {
      setError('Please select a file to upload.')
      return
    }
    setReUploading(true)
    setError('')
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      const formData = new FormData()
      formData.append('file', reUploadFile)
      const res = await axios.post(`/resumes/upload/${applicationId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${token}` },
        timeout: 120000,
      })
      setApplicationDetailData((prev) =>
        prev
          ? {
              ...prev,
              evaluation_scores: res.data.evaluation_scores,
              overall_score: res.data.overall_score,
              suggestions: res.data.suggestions || [],
            }
          : null
      )
      setReUploadFile(null)
      setSuccess('Resume re-uploaded and analyzed successfully.')
      await fetchApplications()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Re-upload failed.')
    } finally {
      setReUploading(false)
    }
  }

  const openInterviewPrepModal = async (appId: number) => {
    setShowInterviewPrepModal(true)
    setInterviewPrepAppId(appId)
    setInterviewPrepData(null)
    setInterviewPrepError('')
    setEvaluationResult(null)
    setPracticeQuestionId(null)
    setPracticeAnswerText('')
    setInterviewPrepLoading(true)
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      const res = await axios.get(`/interview-prep/${appId}`)
      setInterviewPrepData(res.data)
    } catch (err: any) {
      if (err.response?.status === 404) {
        setInterviewPrepData(null)
        setInterviewPrepError('')
      } else {
        setInterviewPrepError(err.response?.data?.detail || 'Failed to load interview prep')
      }
    } finally {
      setInterviewPrepLoading(false)
    }
  }

  const fetchInterviewPrepAfterGenerate = async () => {
    if (interviewPrepAppId == null) return
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      const res = await axios.get(`/interview-prep/${interviewPrepAppId}`)
      setInterviewPrepData(res.data)
    } catch (_) {}
  }

  const handleGeneratePrep = async () => {
    if (interviewPrepAppId == null) return
    setGeneratingPrep(true)
    setInterviewPrepError('')
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      await axios.post('/interview-prep/generate', {
        application_id: interviewPrepAppId,
        days: generateForm.days,
        focus: generateForm.focus,
        difficulty: generateForm.difficulty,
      }, { timeout: 60000 })
      await fetchInterviewPrepAfterGenerate()
    } catch (err: any) {
      setInterviewPrepError(err.response?.data?.detail || 'Failed to generate prep')
    } finally {
      setGeneratingPrep(false)
    }
  }

  const handleEvaluateAnswer = async () => {
    if (!interviewPrepData?.id || !practiceQuestionId?.trim() || !practiceAnswerText.trim()) return
    setEvaluateLoading(true)
    setEvaluationResult(null)
    setInterviewPrepError('')
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      const res = await axios.post('/interview-prep/evaluate', {
        interview_prep_id: interviewPrepData.id,
        question_id: practiceQuestionId,
        answer_text: practiceAnswerText,
      })
      setEvaluationResult(res.data)
    } catch (err: any) {
      setInterviewPrepError(err.response?.data?.detail || 'Evaluation failed')
    } finally {
      setEvaluateLoading(false)
    }
  }

  const startVoiceRecording = () => {
    setVoiceChunks([])
    setInterviewPrepError('')
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      const recorder = new MediaRecorder(stream)
      const chunks: Blob[] = []
      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
      recorder.onstop = () => {
        setVoiceChunks(chunks)
        stream.getTracks().forEach((t) => t.stop())
      }
      recorder.start()
      setVoiceMediaRecorder(recorder)
      setVoiceRecording(true)
    }).catch(() => setInterviewPrepError('Microphone access denied'))
  }

  const stopVoiceRecordingAndSubmit = async () => {
    if (!voiceMediaRecorder) return
    voiceMediaRecorder.stop()
    setVoiceMediaRecorder(null)
    setVoiceRecording(false)
    // Wait a tick for ondataavailable
    await new Promise((r) => setTimeout(r, 300))
  }

  useEffect(() => {
    if (voiceChunks.length === 0) return
    const submitVoice = async () => {
      const blob = new Blob(voiceChunks, { type: 'audio/webm' })
      const file = new File([blob], 'audio.webm', { type: 'audio/webm' })
      if (!interviewPrepData?.id || !practiceQuestionId) return
      setEvaluateLoading(true)
      setEvaluationResult(null)
      setInterviewPrepError('')
      try {
        const token = localStorage.getItem('token')
        if (!token) return
        const form = new FormData()
        form.append('audio_file', file)
        form.append('interview_prep_id', String(interviewPrepData.id))
        form.append('question_id', practiceQuestionId)
        const res = await axios.post('/interview-prep/voice-answer', form, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 60000,
        })
        setEvaluationResult({
          score: res.data.score,
          strengths: res.data.strengths || [],
          missing_points: res.data.missing_points || [],
          improved_answer: res.data.improved_answer || '',
          next_drill: res.data.next_drill || '',
        })
        setPracticeAnswerText(res.data.transcript || '')
      } catch (err: any) {
        setInterviewPrepError(err.response?.data?.detail || 'Voice evaluation failed')
      } finally {
        setEvaluateLoading(false)
        setVoiceChunks([])
      }
    }
    submitVoice()
  }, [voiceChunks])

  useEffect(() => {
    if (showProfileModal && user) {
      setProfileError('')
      setProfileLoading(true)
      const token = localStorage.getItem('token')
      if (!token) {
        setProfileLoading(false)
        return
      }
      axios
        .get('/auth/me', { headers: { Authorization: `Bearer ${token}` } })
        .then((res) => {
          const u = res.data
          setProfileForm({
            name: u.name ?? '',
            email: u.email ?? '',
            highest_degree: u.highest_degree ?? '',
            major: Array.isArray(u.major) ? u.major : [],
            graduation_year: u.graduation_year != null ? String(u.graduation_year) : '',
            country: u.country ?? '',
            primary_industry_preference: u.primary_industry_preference ?? '',
            primary_role_preference: u.primary_role_preference ?? '',
            desired_countries: Array.isArray(u.desired_countries) ? u.desired_countries : [],
            years_experience: u.years_experience != null ? String(u.years_experience) : '',
            remote_preference: u.remote_preference ?? '',
            work_authorization: u.work_authorization ?? '',
            job_type_preference: u.job_type_preference ?? 'Full-time',
          })
        })
        .catch((err) => setProfileError(err.response?.data?.detail || 'Failed to load profile'))
        .finally(() => setProfileLoading(false))
    }
  }, [showProfileModal, user])

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setProfileSaving(true)
    setProfileError('')
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      const payload: Record<string, any> = {}
      if (profileForm.name !== undefined) payload.name = profileForm.name || null
      if (profileForm.highest_degree !== undefined) payload.highest_degree = profileForm.highest_degree || null
      if (profileForm.major !== undefined) payload.major = profileForm.major?.length ? profileForm.major : null
      if (profileForm.graduation_year !== undefined) payload.graduation_year = profileForm.graduation_year ? parseInt(profileForm.graduation_year, 10) : null
      if (profileForm.country !== undefined) payload.country = profileForm.country || null
      if (profileForm.primary_industry_preference !== undefined) payload.primary_industry_preference = profileForm.primary_industry_preference || null
      if (profileForm.primary_role_preference !== undefined) payload.primary_role_preference = profileForm.primary_role_preference || null
      if (profileForm.desired_countries !== undefined) payload.desired_countries = profileForm.desired_countries?.length ? profileForm.desired_countries : null
      if (profileForm.years_experience !== undefined) payload.years_experience = profileForm.years_experience ? parseInt(profileForm.years_experience, 10) : null
      if (profileForm.remote_preference !== undefined) payload.remote_preference = profileForm.remote_preference || null
      if (profileForm.work_authorization !== undefined) payload.work_authorization = profileForm.work_authorization || null
      if (profileForm.job_type_preference !== undefined) payload.job_type_preference = profileForm.job_type_preference || null
      await axios.patch('/auth/me', payload, { headers: { Authorization: `Bearer ${token}` } })
      setSuccess('Profile updated successfully.')
      setShowProfileModal(false)
    } catch (err: any) {
      setProfileError(err.response?.data?.detail || err.message || 'Failed to save profile')
    } finally {
      setProfileSaving(false)
    }
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

        {/* Add Application */}
        <div className="mb-6 flex justify-between items-center gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">My Applications</h2>
            <p className="text-sm text-gray-500 mt-1">
              {applications.length} {applications.length === 1 ? 'application' : 'applications'} tracked
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setError('')
              setSuccess('')
              setShowNewApplicationChoice(true)
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
              <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setError('')
                    setSuccess('')
                    setShowNewApplicationChoice(true)
                  }}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  <svg className="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  New Application
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setError('')
                    setSuccess('')
                    openRecommendationsModal()
                  }}
                  className="inline-flex items-center px-4 py-2 border border-indigo-600 text-indigo-600 shadow-sm text-sm font-medium rounded-md bg-white hover:bg-indigo-50"
                >
                  Browse Job Recommendations
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
                          <button
                            type="button"
                            onClick={() => openApplicationDetail(app.id)}
                            className="text-indigo-600 hover:text-indigo-900 font-medium"
                          >
                            View
                          </button>
                          {app.status === 'Interview Prep' && (
                            <button
                              type="button"
                              onClick={() => openInterviewPrepModal(app.id)}
                              className="text-purple-600 hover:text-purple-900 font-medium"
                            >
                              Prepare
                            </button>
                          )}
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

      {/* Job Recommendations Modal */}
      {showRecommendationsModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <div>
                <h3 className="text-xl font-semibold text-gray-900">Recommended roles based on your profile</h3>
                <p className="text-xs text-gray-500 mt-1">
                  These suggestions use the preferences you set during onboarding (not your resume). You can also skip and add an application manually.
                </p>
              </div>
              <button
                onClick={() => {
                  setShowRecommendationsModal(false)
                }}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>

            <div className="p-6 space-y-4">
              {recommendationsError && (
                <div className="mb-4 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-800">
                  {recommendationsError}
                </div>
              )}

              {loadingRecommendations ? (
                <div className="py-8 text-center text-gray-600 text-sm">
                  Loading personalized job recommendations...
                </div>
              ) : recommendations.length === 0 ? (
                <div className="py-8 text-center text-gray-600 text-sm">
                  No recommendations available right now. You can still add an application manually.
                </div>
              ) : (
                <div className="space-y-3 max-h-[55vh] overflow-y-auto">
                  {recommendations.map((job) => (
                    <div
                      key={job.job_id}
                      className="border rounded-lg p-4 hover:bg-gray-50 transition flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                    >
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900">
                          {job.title}
                        </h4>
                        <p className="text-xs text-gray-600">{job.company}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {job.location_display && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-700">
                              {job.location_display}
                            </span>
                          )}
                          {job.remote_type && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-50 text-indigo-700">
                              {job.remote_type}
                            </span>
                          )}
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-50 text-green-700">
                            Match score: {(job.score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                        {job.url && (
                          <a
                            href={job.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-indigo-600 hover:text-indigo-800"
                          >
                            View posting
                          </a>
                        )}
                        <button
                          type="button"
                          onClick={() => handleUseRecommendation(job)}
                          className="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700"
                        >
                          Use this job
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4 flex flex-col sm:flex-row justify-end gap-3 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => {
                    setShowRecommendationsModal(false)
                  }}
                  className="px-4 py-2 text-xs sm:text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowRecommendationsModal(false)
                    setError('')
                    setSuccess('')
                    setShowAddModal(true)
                  }}
                  className="px-4 py-2 text-xs sm:text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700"
                >
                  Skip – add application manually
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* New Application Choice Modal */}
      {showNewApplicationChoice && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="border-b px-6 py-4 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">Start a new application</h3>
              <button
                type="button"
                onClick={() => setShowNewApplicationChoice(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            <div className="p-6 space-y-4 text-sm text-gray-700">
              <p>How would you like to start?</p>
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowNewApplicationChoice(false)
                    openRecommendationsModal()
                  }}
                  className="w-full inline-flex items-center justify-center px-4 py-2 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-50 font-medium"
                >
                  Browse Job Recommendations
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowNewApplicationChoice(false)
                    setShowAddModal(true)
                  }}
                  className="w-full inline-flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 font-medium"
                >
                  Skip and Add Manually
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                No search is run until you choose an option above.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Application Detail Modal (previous application: resume score + re-upload) */}
      {showApplicationDetailModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center z-10">
              <div>
                <h3 className="text-xl font-semibold text-gray-900">
                  {applicationDetailData
                    ? `${applicationDetailData.application.company_name} – ${applicationDetailData.application.job_title}`
                    : 'Application details'}
                </h3>
                {applicationDetailData && (
                  <p className="text-sm text-gray-500 mt-1">
                    Status: {applicationDetailData.application.status} · Applied {formatDate(applicationDetailData.application.created_at)}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowApplicationDetailModal(false)
                  setApplicationDetailData(null)
                  setReUploadFile(null)
                }}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            <div className="p-6 space-y-6">
              {!applicationDetailData ? (
                <div className="py-12 text-center text-gray-600">Loading...</div>
              ) : applicationDetailData.overall_score != null ? (
                <>
                  <div className="p-6 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border-2 border-indigo-200">
                    <div className="text-center">
                      <div className="text-4xl font-bold text-indigo-600 mb-2">
                        {applicationDetailData.overall_score?.toFixed(1) ?? 'N/A'}
                      </div>
                      <div className="text-lg text-gray-700">Resume score (latest)</div>
                      <div className="text-sm text-gray-500 mt-1">Out of 100 points</div>
                    </div>
                  </div>
                  <div className="space-y-4">
                    {applicationDetailData.evaluation_scores?.format && (
                      <div className="border rounded-lg overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setDetailExpandedSections((s) => ({ ...s, format: !s.format }))}
                          className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
                        >
                          <span className="text-lg font-semibold text-gray-900">Format & Structure</span>
                          <span className="text-gray-600">
                            {applicationDetailData.evaluation_scores.format.score?.toFixed(1) ?? 'N/A'}
                          </span>
                        </button>
                        {detailExpandedSections.format && (
                          <div className="px-6 py-4 border-t bg-gray-50 text-sm text-gray-700">
                            {applicationDetailData.evaluation_scores.format.strengths?.length > 0 && (
                              <>
                                <p className="font-medium text-green-700 mb-1">Strengths:</p>
                                <ul className="list-disc list-inside mb-2">{applicationDetailData.evaluation_scores.format.strengths.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul>
                              </>
                            )}
                            {applicationDetailData.evaluation_scores.format.issues?.length > 0 && (
                              <>
                                <p className="font-medium text-red-700 mb-1">Areas to improve:</p>
                                <ul className="list-disc list-inside">{applicationDetailData.evaluation_scores.format.issues.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    {applicationDetailData.evaluation_scores?.grammar && (
                      <div className="border rounded-lg overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setDetailExpandedSections((s) => ({ ...s, grammar: !s.grammar }))}
                          className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
                        >
                          <span className="text-lg font-semibold text-gray-900">Grammar & Spelling</span>
                          <span className="text-gray-600">
                            {applicationDetailData.evaluation_scores.grammar.score?.toFixed(1) ?? 'N/A'}
                          </span>
                        </button>
                        {detailExpandedSections.grammar && (
                          <div className="px-6 py-4 border-t bg-gray-50 text-sm text-gray-700">
                            {applicationDetailData.evaluation_scores.grammar.error_count === 0
                              ? 'No errors detected.'
                              : `${applicationDetailData.evaluation_scores.grammar.error_count} errors found.`}
                          </div>
                        )}
                      </div>
                    )}
                    {applicationDetailData.evaluation_scores?.job_compatibility && (
                      <div className="border rounded-lg overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setDetailExpandedSections((s) => ({ ...s, job_compatibility: !s.job_compatibility }))}
                          className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
                        >
                          <span className="text-lg font-semibold text-gray-900">Job Compatibility</span>
                          <span className="text-gray-600">
                            {applicationDetailData.evaluation_scores.job_compatibility.score?.toFixed(1) ?? 'N/A'}
                          </span>
                        </button>
                        {detailExpandedSections.job_compatibility && (
                          <div className="px-6 py-4 border-t bg-gray-50 text-sm text-gray-700">
                            Matched / missing skills and similarity with job description.
                          </div>
                        )}
                      </div>
                    )}
                    {applicationDetailData.evaluation_scores?.content_depth && (
                      <div className="border rounded-lg overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setDetailExpandedSections((s) => ({ ...s, content_depth: !s.content_depth }))}
                          className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
                        >
                          <span className="text-lg font-semibold text-gray-900">Content Depth</span>
                          <span className="text-gray-600">
                            {applicationDetailData.evaluation_scores.content_depth.score?.toFixed(1) ?? 'N/A'}
                          </span>
                        </button>
                        {detailExpandedSections.content_depth && (
                          <div className="px-6 py-4 border-t bg-gray-50 text-sm text-gray-700">
                            Action verbs, quantification, clichés.
                          </div>
                        )}
                      </div>
                    )}
                    {applicationDetailData.suggestions?.length > 0 && (
                      <div className="border rounded-lg p-4 bg-blue-50">
                        <h4 className="font-semibold text-gray-900 mb-2">Suggestions</h4>
                        <ol className="list-decimal list-inside text-sm text-gray-700 space-y-1">
                          {applicationDetailData.suggestions.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="py-6 text-center text-gray-600">
                  No resume uploaded for this application yet. You can upload one below.
                </div>
              )}
              {applicationDetailData && (
                <div className="border-t pt-6">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Re-upload resume (new version)</h4>
                  <div className="flex flex-wrap items-center gap-3">
                    <label className="flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800 cursor-pointer">
                      <input
                        type="file"
                        className="sr-only"
                        accept=".pdf,.doc,.docx"
                        onChange={(e) => setReUploadFile(e.target.files?.[0] ?? null)}
                      />
                      <span className="font-medium">Choose file</span>
                    </label>
                    {reUploadFile && <span className="text-sm text-gray-600">{reUploadFile.name}</span>}
                    <button
                      type="button"
                      disabled={!reUploadFile || reUploading}
                      onClick={() => handleReUploadResume(applicationDetailData.application.id)}
                      className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {reUploading ? 'Analyzing...' : 'Re-upload & analyze'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Interview Prep Modal */}
      {showInterviewPrepModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="relative bg-white rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden border border-slate-200 flex flex-col">
            <div className="flex justify-between items-center px-6 py-4 border-b bg-gradient-to-r from-indigo-600 to-slate-900">
              <div>
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  Interview Preparation
                  {interviewPrepAppId != null && applications.find((a) => a.id === interviewPrepAppId) && (
                    <span className="text-indigo-100 font-normal text-xs">
                      · {applications.find((a) => a.id === interviewPrepAppId)?.company_name} · {applications.find((a) => a.id === interviewPrepAppId)?.job_title}
                    </span>
                  )}
                </h3>
                <p className="text-[11px] text-indigo-100/90">
                  Questions and feedback grounded in your resume and this specific role.
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowInterviewPrepModal(false)
                  setInterviewPrepAppId(null)
                  setInterviewPrepData(null)
                  setPracticeQuestionId(null)
                  setEvaluationResult(null)
                }}
                className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20 text-xl"
              >
                ×
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 bg-slate-50/70 space-y-6">
              {interviewPrepError && (
                <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-800">{interviewPrepError}</div>
              )}
              {interviewPrepLoading ? (
                <div className="py-12 flex flex-col items-center justify-center text-slate-600">
                  <div className="h-8 w-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3" />
                  <p className="text-sm">Loading interview prep…</p>
                </div>
              ) : !interviewPrepData ? (
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="rounded-xl bg-white border border-slate-200 p-5 shadow-sm">
                    <h4 className="text-sm font-semibold text-slate-900 mb-2">Generation settings</h4>
                    <p className="text-xs text-slate-600 mb-4">
                      Use your resume and this job description to generate a structured prep package.
                    </p>
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">Preparation days</label>
                        <input
                          type="number"
                          min={1}
                          max={14}
                          value={generateForm.days}
                          onChange={(e) => setGenerateForm((f) => ({ ...f, days: Number(e.target.value) || 7 }))}
                          className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">Difficulty</label>
                        <select
                          value={generateForm.difficulty}
                          onChange={(e) => setGenerateForm((f) => ({ ...f, difficulty: e.target.value }))}
                          className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
                        >
                          <option value="easy">Easy</option>
                          <option value="mixed">Mixed</option>
                          <option value="hard">Hard</option>
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">Focus areas</label>
                      <div className="flex flex-wrap gap-2">
                        {['technical', 'behavioral', 'case', 'resume'].map((f) => {
                          const active = generateForm.focus.includes(f)
                          return (
                            <button
                              key={f}
                              type="button"
                              onClick={() =>
                                setGenerateForm((prev) => ({
                                  ...prev,
                                  focus: active ? prev.focus.filter((x) => x !== f) : [...prev.focus, f],
                                }))
                              }
                              className={`px-3 py-1 rounded-full text-xs border ${
                                active
                                  ? 'bg-indigo-50 text-indigo-700 border-indigo-300'
                                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                              }`}
                            >
                              {f[0].toUpperCase() + f.slice(1)}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                    <div className="mt-4">
                      <button
                        type="button"
                        disabled={generatingPrep}
                        onClick={handleGeneratePrep}
                        className="w-full inline-flex justify-center items-center px-4 py-2 rounded-md bg-indigo-600 text-white text-sm font-medium shadow-sm hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {generatingPrep ? 'Generating…' : 'Generate prep'}
                      </button>
                    </div>
                  </div>
                  <div className="rounded-xl border border-dashed border-slate-300 bg-slate-100/80 p-5 flex flex-col justify-center">
                    <h4 className="text-sm font-semibold text-slate-900 mb-2">What you’ll get</h4>
                    <ul className="text-xs text-slate-700 space-y-1">
                      <li>• Role summary and key requirements for this job.</li>
                      <li>• 8 tailored technical, behavioral, and resume-based questions.</li>
                      <li>• Highlighted skill gaps vs. the job description.</li>
                      <li>• A rubric the AI uses to score your answers.</li>
                    </ul>
                  </div>
                </div>
              ) : !interviewPrepData.generated_json ? (
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="rounded-xl bg-white border border-slate-200 p-5 shadow-sm">
                    <h4 className="text-sm font-semibold text-slate-900 mb-2">Generation settings</h4>
                    <p className="text-xs text-slate-600 mb-4">
                      Generate a fresh prep package for this application.
                    </p>
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">Preparation days</label>
                        <input
                          type="number"
                          min={1}
                          max={14}
                          value={generateForm.days}
                          onChange={(e) => setGenerateForm((f) => ({ ...f, days: Number(e.target.value) || 7 }))}
                          className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">Difficulty</label>
                        <select
                          value={generateForm.difficulty}
                          onChange={(e) => setGenerateForm((f) => ({ ...f, difficulty: e.target.value }))}
                          className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
                        >
                          <option value="easy">Easy</option>
                          <option value="mixed">Mixed</option>
                          <option value="hard">Hard</option>
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">Focus areas</label>
                      <div className="flex flex-wrap gap-2">
                        {['technical', 'behavioral', 'case', 'resume'].map((f) => {
                          const active = generateForm.focus.includes(f)
                          return (
                            <button
                              key={f}
                              type="button"
                              onClick={() =>
                                setGenerateForm((prev) => ({
                                  ...prev,
                                  focus: active ? prev.focus.filter((x) => x !== f) : [...prev.focus, f],
                                }))
                              }
                              className={`px-3 py-1 rounded-full text-xs border ${
                                active
                                  ? 'bg-indigo-50 text-indigo-700 border-indigo-300'
                                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                              }`}
                            >
                              {f[0].toUpperCase() + f.slice(1)}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                    <div className="mt-4">
                      <button
                        type="button"
                        disabled={generatingPrep}
                        onClick={handleGeneratePrep}
                        className="w-full inline-flex justify-center items-center px-4 py-2 rounded-md bg-indigo-600 text-white text-sm font-medium shadow-sm hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {generatingPrep ? 'Generating…' : 'Generate prep'}
                      </button>
                    </div>
                  </div>
                  <div className="rounded-xl border border-dashed border-slate-300 bg-slate-100/80 p-5 flex flex-col justify-center">
                    <h4 className="text-sm font-semibold text-slate-900 mb-2">What you’ll get</h4>
                    <ul className="text-xs text-slate-700 space-y-1">
                      <li>• Role summary and key requirements for this job.</li>
                      <li>• 8 tailored technical, behavioral, and resume-based questions.</li>
                      <li>• Highlighted skill gaps vs. the job description.</li>
                      <li>• A rubric the AI uses to score your answers.</li>
                    </ul>
                  </div>
                </div>
              ) : !interviewPrepData.generated_json ? (
                <div className="space-y-4">
                  <p className="text-gray-700">Generate tailored interview preparation.</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Preparation days</label>
                      <input
                        type="number"
                        min={1}
                        max={14}
                        value={generateForm.days}
                        onChange={(e) => setGenerateForm((f) => ({ ...f, days: Number(e.target.value) || 7 }))}
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty</label>
                      <select
                        value={generateForm.difficulty}
                        onChange={(e) => setGenerateForm((f) => ({ ...f, difficulty: e.target.value }))}
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="easy">Easy</option>
                        <option value="mixed">Mixed</option>
                        <option value="hard">Hard</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Focus areas</label>
                    <div className="flex flex-wrap gap-2">
                      {['technical', 'behavioral', 'case', 'resume'].map((f) => (
                        <label key={f} className="inline-flex items-center">
                          <input
                            type="checkbox"
                            checked={generateForm.focus.includes(f)}
                            onChange={(e) => {
                              setGenerateForm((prev) => ({
                                ...prev,
                                focus: e.target.checked ? [...prev.focus, f] : prev.focus.filter((x) => x !== f),
                              }))
                            }}
                            className="rounded border-gray-300 text-indigo-600"
                          />
                          <span className="ml-1 text-sm text-gray-700 capitalize">{f}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={generatingPrep}
                    onClick={handleGeneratePrep}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {generatingPrep ? 'Generating...' : 'Generate prep'}
                  </button>
                </div>
              ) : (
                <>
                  {interviewPrepData.generated_json.role_context && (
                    <div className="border rounded-lg p-4 bg-gray-50">
                      <h4 className="font-semibold text-gray-900 mb-2">Role context</h4>
                      <p className="text-sm text-gray-700">
                        {interviewPrepData.generated_json.role_context.target_title} · {interviewPrepData.generated_json.role_context.seniority}
                        {interviewPrepData.generated_json.role_context.company && ` · ${interviewPrepData.generated_json.role_context.company}`}
                      </p>
                      {interviewPrepData.generated_json.role_context.key_requirements?.length ? (
                        <ul className="mt-1 list-disc list-inside text-sm text-gray-600">
                          {interviewPrepData.generated_json.role_context.key_requirements.slice(0, 5).map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                  )}
                  {interviewPrepData.generated_json.study_plan && interviewPrepData.generated_json.study_plan.length > 0 && (
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold text-gray-900 mb-2">Study plan</h4>
                      <ul className="space-y-2 text-sm text-gray-700">
                        {interviewPrepData.generated_json.study_plan.map((day) => (
                          <li key={day.day}>
                            <span className="font-medium">Day {day.day}:</span> {day.focus} – {day.deliverable}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {interviewPrepData.generated_json.skill_gaps && (
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold text-gray-900 mb-2">Skill gaps</h4>
                      <p className="text-sm text-gray-600">
                        Matched: {interviewPrepData.generated_json.skill_gaps.matched?.join(', ') || '—'} · Missing: {interviewPrepData.generated_json.skill_gaps.missing?.join(', ') || '—'}
                      </p>
                    </div>
                  )}
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Practice questions</h4>
                    <div className="space-y-4">
                      {(interviewPrepData.generated_json.questions || []).map((q) => (
                        <div key={q.id} className="border rounded-lg p-4">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <span className="text-xs text-gray-500 uppercase">{q.type}</span>
                              <p className="font-medium text-gray-900 mt-0.5">{q.question}</p>
                              {q.what_good_looks_like && q.what_good_looks_like.length > 0 && (
                                <ul className="mt-1 text-sm text-gray-600 list-disc list-inside">
                                  {q.what_good_looks_like.slice(0, 3).map((b, i) => (
                                    <li key={i}>{b}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                setPracticeQuestionId(q.id)
                                setPracticeAnswerText('')
                                setEvaluationResult(null)
                              }}
                              className={`text-sm px-2 py-1 rounded ${practiceQuestionId === q.id ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                            >
                              Practice
                            </button>
                          </div>
                          {practiceQuestionId === q.id && (
                            <div className="mt-4 pt-4 border-t">
                              <label className="block text-sm font-medium text-gray-700 mb-1">Your answer (type or record)</label>
                              <textarea
                                value={practiceAnswerText}
                                onChange={(e) => setPracticeAnswerText(e.target.value)}
                                placeholder="Type your answer here..."
                                rows={4}
                                className="block w-full px-3 py-2 border border-gray-300 rounded-md"
                              />
                              <div className="mt-2 flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  disabled={evaluateLoading || !practiceAnswerText.trim()}
                                  onClick={handleEvaluateAnswer}
                                  className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                                >
                                  {evaluateLoading ? 'Evaluating...' : 'Get feedback'}
                                </button>
                                <button
                                  type="button"
                                  onClick={voiceRecording ? stopVoiceRecordingAndSubmit : startVoiceRecording}
                                  className={`px-3 py-1.5 text-sm rounded-md ${voiceRecording ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
                                >
                                  {voiceRecording ? 'Stop & submit' : 'Record answer'}
                                </button>
                              </div>
                              {evaluationResult && (
                                <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-2">
                                  <p className="font-medium text-gray-900">Score: {evaluationResult.score}/5</p>
                                  {evaluationResult.strengths?.length > 0 && (
                                    <p className="text-sm text-green-700"><span className="font-medium">Strengths:</span> {evaluationResult.strengths.join(' ')}</p>
                                  )}
                                  {evaluationResult.missing_points?.length > 0 && (
                                    <p className="text-sm text-amber-700"><span className="font-medium">To improve:</span> {evaluationResult.missing_points.join(' ')}</p>
                                  )}
                                  {evaluationResult.improved_answer && (
                                    <p className="text-sm text-gray-700"><span className="font-medium">Improved answer:</span> {evaluationResult.improved_answer}</p>
                                  )}
                                  {evaluationResult.next_drill && (
                                    <p className="text-sm text-gray-600"><span className="font-medium">Next drill:</span> {evaluationResult.next_drill}</p>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

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

                {/* Job Compatibility - Only shown when JD exists */}
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
                          <p className="text-sm text-gray-500">Skill coverage and semantic similarity</p>
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
                        {/* JD Skill Coverage */}
                        {evaluationResults.evaluation_scores.job_compatibility.skill_coverage !== undefined && (
                          <div className="mb-4 bg-white p-3 rounded border">
                            <p className="text-sm font-semibold text-gray-900 mb-2">JD Skill Coverage</p>
                            <p className="text-sm font-medium text-gray-700 mb-1">
                              Coverage: {(evaluationResults.evaluation_scores.job_compatibility.skill_coverage * 100).toFixed(1)}%
                            </p>
                            <p className="text-xs text-gray-500">
                              {evaluationResults.evaluation_scores.job_compatibility.matched_skills?.length || 0} of {evaluationResults.evaluation_scores.job_compatibility.job_skills?.length || 0} required skills found
                            </p>
                          </div>
                        )}
                        
                        {evaluationResults.evaluation_scores.job_compatibility.matched_skills?.length > 0 && (
                          <div className="mb-4">
                            <p className="text-sm font-semibold text-green-700 mb-2">✓ Matched Skills ({evaluationResults.evaluation_scores.job_compatibility.matched_skills.length}):</p>
                            <div className="flex flex-wrap gap-2">
                              {evaluationResults.evaluation_scores.job_compatibility.matched_skills.map((skill: string, idx: number) => (
                                <span key={idx} className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {evaluationResults.evaluation_scores.job_compatibility.missing_skills?.length > 0 && (
                          <div className="mb-4">
                            <p className="text-sm font-semibold text-red-700 mb-2">⚠ Missing Skills ({evaluationResults.evaluation_scores.job_compatibility.missing_skills.length}):</p>
                            <div className="flex flex-wrap gap-2">
                              {evaluationResults.evaluation_scores.job_compatibility.missing_skills.map((skill: string, idx: number) => (
                                <span key={idx} className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">
                                  {skill}
                                </span>
                              ))}
                            </div>
                            <p className="text-xs text-gray-600 mt-2">Consider adding these skills to improve compatibility</p>
                          </div>
                        )}
                        
                        {evaluationResults.evaluation_scores.job_compatibility.embedding_similarity !== undefined && evaluationResults.evaluation_scores.job_compatibility.embedding_similarity > 0 && (
                          <div className="bg-white p-3 rounded border">
                            <p className="text-sm font-medium text-gray-700">Semantic Similarity: {(evaluationResults.evaluation_scores.job_compatibility.embedding_similarity * 100).toFixed(1)}%</p>
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

                {/* Content Depth Score */}
                <div className="border rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedSections({...expandedSections, content_depth: !expandedSections.content_depth})}
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="text-2xl font-bold text-gray-700">
                        {evaluationResults.evaluation_scores?.content_depth?.score?.toFixed(1) || 'N/A'}
                      </div>
                      <div>
                        <h4 className="text-lg font-semibold text-gray-900">Content Depth</h4>
                        <p className="text-sm text-gray-500">Action verbs, quantification, clichés, skills</p>
                      </div>
                    </div>
                    <svg
                      className={`w-5 h-5 text-gray-500 transform transition-transform ${expandedSections.content_depth ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {expandedSections.content_depth && (
                    <div className="px-6 py-4 border-t bg-gray-50 space-y-4">
                      {/* Strengths */}
                      {evaluationResults.evaluation_scores?.content_depth?.strengths?.length > 0 && (
                        <div>
                          <p className="text-sm font-semibold text-green-700 mb-2">✓ What's Working Well:</p>
                          <ul className="list-none space-y-1">
                            {evaluationResults.evaluation_scores.content_depth.strengths.map((strength: string, idx: number) => (
                              <li key={idx} className="text-sm text-green-600">{strength}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Issues */}
                      {evaluationResults.evaluation_scores?.content_depth?.issues?.length > 0 && (
                        <div>
                          <p className="text-sm font-semibold text-red-700 mb-2">⚠ Areas to Improve:</p>
                          <ul className="list-disc list-inside text-sm text-red-600 space-y-1">
                            {evaluationResults.evaluation_scores.content_depth.issues.map((issue: string, idx: number) => (
                              <li key={idx}>{issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Clichés */}
                      {evaluationResults.evaluation_scores?.content_depth?.cliches_found?.length > 0 && (
                        <div>
                          <p className="text-sm font-semibold text-yellow-700 mb-2">⚠ Clichés Found ({evaluationResults.evaluation_scores.content_depth.cliches_found.length}):</p>
                          <div className="flex flex-wrap gap-2">
                            {evaluationResults.evaluation_scores.content_depth.cliches_found.map((cliche: string, idx: number) => (
                              <span key={idx} className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">
                                {cliche}
                              </span>
                            ))}
                          </div>
                          <p className="text-xs text-gray-600 mt-2">Replace these with specific, measurable achievements</p>
                        </div>
                      )}
                      
                      {/* Detailed Breakdown */}
                      {evaluationResults.evaluation_scores?.content_depth?.details && (
                        <div className="mt-4 space-y-3 text-sm">
                          {evaluationResults.evaluation_scores.content_depth.details.action_verbs && (
                            <div className="bg-white p-3 rounded border">
                              <p className="font-medium text-gray-700 mb-1">Action Verbs:</p>
                              <p className="text-gray-600">{evaluationResults.evaluation_scores.content_depth.details.action_verbs.score_breakdown}</p>
                              {evaluationResults.evaluation_scores.content_depth.details.action_verbs.examples_strong?.length > 0 && (
                                <p className="text-green-600 text-xs mt-1">
                                  Strong verbs used: {evaluationResults.evaluation_scores.content_depth.details.action_verbs.examples_strong.join(', ')}
                                </p>
                              )}
                            </div>
                          )}
                          
                          {evaluationResults.evaluation_scores.content_depth.details.quantification && (
                            <div className="bg-white p-3 rounded border">
                              <p className="font-medium text-gray-700 mb-1">Quantification:</p>
                              <p className="text-gray-600">{evaluationResults.evaluation_scores.content_depth.details.quantification.score_breakdown}</p>
                              {evaluationResults.evaluation_scores.content_depth.details.quantification.bullets_with_numbers > 0 && (
                                <p className="text-gray-500 text-xs mt-1">
                                  {evaluationResults.evaluation_scores.content_depth.details.quantification.bullets_with_numbers} bullets with numbers
                                  {evaluationResults.evaluation_scores.content_depth.details.quantification.bullets_with_percentages > 0 && 
                                    `, ${evaluationResults.evaluation_scores.content_depth.details.quantification.bullets_with_percentages} with percentages`}
                                </p>
                              )}
                            </div>
                          )}
                          
                          {evaluationResults.evaluation_scores.content_depth.details.skills && (
                            <div className="bg-white p-3 rounded border">
                              <p className="font-medium text-gray-700 mb-1">Skills:</p>
                              <p className="text-gray-600">{evaluationResults.evaluation_scores.content_depth.details.skills.score_breakdown}</p>
                              {evaluationResults.evaluation_scores.content_depth.details.skills.missing_skills?.length > 0 && (
                                <p className="text-red-600 text-xs mt-1">
                                  Consider adding: {evaluationResults.evaluation_scores.content_depth.details.skills.missing_skills.slice(0, 5).join(', ')}
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

      {/* Edit Profile Modal */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <h3 className="text-xl font-semibold text-gray-900">Edit profile & preferences</h3>
              <button
                type="button"
                onClick={() => setShowProfileModal(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            <form onSubmit={handleSaveProfile} className="p-6 space-y-4">
              {profileError && (
                <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-800">
                  {profileError}
                </div>
              )}
              {profileLoading ? (
                <div className="py-8 text-center text-gray-600">Loading profile...</div>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                    <input
                      type="text"
                      value={profileForm.name ?? ''}
                      onChange={(e) => setProfileForm((p) => ({ ...p, name: e.target.value }))}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input
                      type="email"
                      value={profileForm.email ?? ''}
                      readOnly
                      className="block w-full px-3 py-2 border border-gray-200 rounded-md bg-gray-50 text-gray-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Email cannot be changed here.</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Highest degree</label>
                    <SearchableSelect
                      options={ALL_DEGREE_TYPES}
                      selected={profileForm.highest_degree ? [profileForm.highest_degree] : []}
                      onChange={(selected) => setProfileForm((p) => ({ ...p, highest_degree: selected[0] || '' }))}
                      placeholder="Select degree"
                      multiple={false}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Field(s) of study / Major</label>
                    <SearchableSelect
                      options={ALL_FIELDS_OF_STUDY}
                      selected={profileForm.major ?? []}
                      onChange={(major) => setProfileForm((p) => ({ ...p, major }))}
                      placeholder="Select field(s) of study"
                      multiple={true}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Graduation year</label>
                    <input
                      type="number"
                      min="1950"
                      max="2030"
                      value={profileForm.graduation_year ?? ''}
                      onChange={(e) => setProfileForm((p) => ({ ...p, graduation_year: e.target.value }))}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
                    <SearchableSelect
                      options={ALL_COUNTRIES}
                      selected={profileForm.country ? [profileForm.country] : []}
                      onChange={(selected) => setProfileForm((p) => ({ ...p, country: selected[0] || '' }))}
                      placeholder="Select country"
                      multiple={false}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Primary role preference</label>
                    <input
                      type="text"
                      value={profileForm.primary_role_preference ?? ''}
                      onChange={(e) => setProfileForm((p) => ({ ...p, primary_role_preference: e.target.value }))}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="e.g. Software Engineer, Data Analyst"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Industry preference</label>
                    <SearchableSelect
                      options={ALL_INDUSTRIES}
                      selected={profileForm.primary_industry_preference ? [profileForm.primary_industry_preference] : []}
                      onChange={(selected) => setProfileForm((p) => ({ ...p, primary_industry_preference: selected[0] || '' }))}
                      placeholder="Select industry"
                      multiple={false}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Countries you would like to work in</label>
                    <SearchableSelect
                      options={ALL_COUNTRIES}
                      selected={profileForm.desired_countries ?? []}
                      onChange={(desired_countries) => setProfileForm((p) => ({ ...p, desired_countries }))}
                      placeholder="Select countries"
                      multiple={true}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Years of experience</label>
                    <input
                      type="number"
                      min="0"
                      max="50"
                      value={profileForm.years_experience ?? ''}
                      onChange={(e) => setProfileForm((p) => ({ ...p, years_experience: e.target.value }))}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Work location preference</label>
                    <select
                      value={profileForm.remote_preference ?? ''}
                      onChange={(e) => setProfileForm((p) => ({ ...p, remote_preference: e.target.value }))}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value="">Select</option>
                      <option value="Remote">Remote</option>
                      <option value="On-site">On-site</option>
                      <option value="Hybrid">Hybrid</option>
                      <option value="Any">Any</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Work authorization</label>
                    <select
                      value={profileForm.work_authorization ?? ''}
                      onChange={(e) => setProfileForm((p) => ({ ...p, work_authorization: e.target.value }))}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value="">Select</option>
                      <option value="I can work without sponsorship">I can work without sponsorship</option>
                      <option value="I need sponsorship">I need sponsorship</option>
                      <option value="Not sure">Not sure</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Job type preference</label>
                    <select
                      value={profileForm.job_type_preference ?? 'Full-time'}
                      onChange={(e) => setProfileForm((p) => ({ ...p, job_type_preference: e.target.value }))}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value="Full-time">Full-time</option>
                      <option value="Part-time">Part-time</option>
                      <option value="Internship">Internship</option>
                      <option value="Any">Any</option>
                    </select>
                  </div>
                  <div className="flex justify-end gap-3 pt-4 border-t">
                    <button
                      type="button"
                      onClick={() => setShowProfileModal(false)}
                      className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={profileSaving}
                      className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {profileSaving ? 'Saving...' : 'Save profile'}
                    </button>
                  </div>
                </>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
