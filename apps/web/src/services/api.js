import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Auth
export const login = async (password) => {
  const response = await api.post('/api/auth/login', { password })
  return response.data
}

// Projects
export const getProjects = async () => {
  const response = await api.get('/api/projects')
  return response.data
}

export const getProject = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}`)
  return response.data
}

export const createProject = async (name) => {
  const response = await api.post('/api/projects', { name })
  return response.data
}

export const deleteProject = async (projectId) => {
  const response = await api.delete(`/api/projects/${projectId}`)
  return response.data
}

// Project Files
export const getProjectFiles = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}/files`)
  return response.data
}

export const uploadProjectFile = async (projectId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post(`/api/projects/${projectId}/files`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export const deleteProjectFile = async (projectId, filename) => {
  const response = await api.delete(`/api/projects/${projectId}/files/${encodeURIComponent(filename)}`)
  return response.data
}

// Pipeline Status
export const getProjectStatus = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}/status`)
  return response.data
}

// Workflow Sections (CRUD)
export const getSections = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}/sections`)
  return response.data
}

export const createSection = async (projectId, sectionData) => {
  const response = await api.post(`/api/projects/${projectId}/sections`, sectionData)
  return response.data
}

export const updateSection = async (projectId, sectionId, sectionData) => {
  const response = await api.put(`/api/projects/${projectId}/sections/${sectionId}`, sectionData)
  return response.data
}

export const deleteSection = async (projectId, sectionId) => {
  const response = await api.delete(`/api/projects/${projectId}/sections/${sectionId}`)
  return response.data
}

// Section Questions (CRUD)
export const getQuestions = async (projectId, sectionId) => {
  const response = await api.get(`/api/projects/${projectId}/sections/${sectionId}/questions`)
  return response.data
}

export const createQuestion = async (projectId, sectionId, questionData) => {
  const response = await api.post(`/api/projects/${projectId}/sections/${sectionId}/questions`, questionData)
  return response.data
}

export const updateQuestion = async (projectId, sectionId, questionId, questionData) => {
  const response = await api.put(`/api/projects/${projectId}/sections/${sectionId}/questions/${questionId}`, questionData)
  return response.data
}

export const deleteQuestion = async (projectId, sectionId, questionId) => {
  const response = await api.delete(`/api/projects/${projectId}/sections/${sectionId}/questions/${questionId}`)
  return response.data
}

// Workflows
export const getWorkflows = async (projectId = null) => {
  const params = projectId ? { project_id: projectId } : {}
  const response = await api.get('/api/workflows', { params })
  return response.data
}

export const runWorkflow = async (sectionId, projectId) => {
  const response = await api.post(`/api/workflows/${sectionId}/run`, {
    project_id: projectId,
  })
  return response.data
}

export const getWorkflowStatus = async (sectionId, taskId) => {
  const response = await api.get(`/api/workflows/${sectionId}/status/${taskId}`)
  return response.data
}

export const getResults = async (projectId) => {
  const response = await api.get(`/api/workflows/results/${projectId}`)
  return response.data
}

export const exportResults = async (projectId) => {
  const response = await api.get(`/api/workflows/results/${projectId}/export`, {
    responseType: 'blob',
  })
  return response.data
}

export const clearSectionAnswers = async (sectionId, projectId) => {
  const response = await api.delete(`/api/workflows/${sectionId}/answers/${projectId}`)
  return response.data
}

export const getSectionQuestions = async (sectionId) => {
  const response = await api.get(`/api/workflows/${sectionId}/questions`)
  return response.data
}

export const updateSectionQuestions = async (sectionId, questions) => {
  const response = await api.put(`/api/workflows/${sectionId}/questions`, questions)
  return response.data
}

export const exportSectionQuestions = async (sectionId) => {
  const response = await api.get(`/api/workflows/${sectionId}/questions/export`, {
    responseType: 'blob',
  })
  return response.data
}

export const importSectionQuestions = async (sectionId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post(`/api/workflows/${sectionId}/questions/import`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

// Query
export const queryDocuments = async (query, projectId = null) => {
  const response = await api.post('/api/query', {
    query,
    project_id: projectId,
  })
  return response.data
}

// Indexes
export const getIndexes = async () => {
  const response = await api.get('/api/indexes')
  return response.data
}

export const getActiveIndex = async () => {
  const response = await api.get('/api/indexes/active')
  return response.data
}

export const setActiveIndex = async (indexName) => {
  const response = await api.put('/api/indexes/active', {
    index_name: indexName,
  })
  return response.data
}

// Pipeline
export const getPipelineStages = async () => {
  const response = await api.get('/api/pipeline/stages')
  return response.data
}

export const runPipelineStage = async (projectId, stage, options = {}) => {
  const response = await api.post(`/api/pipeline/${projectId}/run`, { stage, ...options })
  return response.data
}

export const runFullPipeline = async (projectId) => {
  const response = await api.post(`/api/pipeline/${projectId}/run-all`)
  return response.data
}

export const getProjectTasks = async (projectId) => {
  const response = await api.get(`/api/pipeline/${projectId}/tasks`)
  return response.data
}

export const getTaskStatus = async (taskId) => {
  const response = await api.get(`/api/pipeline/tasks/${taskId}`)
  return response.data
}

// Rollback Operations
export const previewRollback = async (projectId, stage, cascade = true) => {
  const response = await api.get(`/api/rollback/${projectId}/preview/${stage}?cascade=${cascade}`)
  return response.data
}

export const rollbackStage = async (projectId, stage, cascade = true) => {
  const response = await api.post(`/api/rollback/${projectId}/rollback/${stage}?cascade=${cascade}`)
  return response.data
}

export const rollbackToStage = async (projectId, targetStage) => {
  const response = await api.post(`/api/rollback/${projectId}/rollback-to/${targetStage}`)
  return response.data
}

export const clearAllOutput = async (projectId) => {
  const response = await api.delete(`/api/rollback/${projectId}/clear-all`)
  return response.data
}

export default {
  login,
  // Projects
  getProjects,
  getProject,
  createProject,
  deleteProject,
  // Files
  getProjectFiles,
  uploadProjectFile,
  deleteProjectFile,
  // Pipeline
  getProjectStatus,
  // Sections
  getSections,
  createSection,
  updateSection,
  deleteSection,
  // Questions
  getQuestions,
  createQuestion,
  updateQuestion,
  deleteQuestion,
  // Workflows
  getWorkflows,
  runWorkflow,
  getWorkflowStatus,
  getResults,
  exportResults,
  clearSectionAnswers,
  getSectionQuestions,
  updateSectionQuestions,
  exportSectionQuestions,
  importSectionQuestions,
  // Query
  queryDocuments,
  // Indexes
  getIndexes,
  getActiveIndex,
  setActiveIndex,
  // Pipeline
  getPipelineStages,
  runPipelineStage,
  runFullPipeline,
  getProjectTasks,
  getTaskStatus,
  // Rollback
  previewRollback,
  rollbackStage,
  rollbackToStage,
  clearAllOutput,
}
