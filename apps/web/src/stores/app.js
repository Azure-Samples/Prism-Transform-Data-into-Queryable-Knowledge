import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

export const useAppStore = defineStore('app', () => {
  const selectedProject = ref('')
  const projects = ref([])
  const activeIndex = ref('')

  // Chat context - the question being discussed (null = general search mode)
  const chatContext = ref(null)
  // Chat conversation history
  const chatHistory = ref([])

  const loadProjects = async () => {
    try {
      const data = await api.getProjects()
      projects.value = data
      // Set first project as selected if none selected
      if (projects.value.length > 0 && !selectedProject.value) {
        selectedProject.value = projects.value[0].name
      }
    } catch (error) {
      console.error('Failed to load projects:', error)
    }
  }

  const loadActiveIndex = async () => {
    try {
      const data = await api.getActiveIndex()
      activeIndex.value = data.name
    } catch (error) {
      console.error('Failed to load active index:', error)
    }
  }

  const setSelectedProject = (projectId) => {
    selectedProject.value = projectId
    // Clear chat when project changes
    clearChat()
  }

  // Set chat context for discussing a specific question
  const setChatContext = (context) => {
    chatContext.value = context
    chatHistory.value = []  // Clear history when context changes
  }

  // Clear chat context (go to general search mode)
  const clearChatContext = () => {
    chatContext.value = null
    chatHistory.value = []
  }

  // Add a message to chat history
  const addChatMessage = (role, content) => {
    chatHistory.value.push({ role, content })
  }

  // Clear all chat state
  const clearChat = () => {
    chatContext.value = null
    chatHistory.value = []
  }

  return {
    selectedProject,
    projects,
    activeIndex,
    chatContext,
    chatHistory,
    loadProjects,
    loadActiveIndex,
    setSelectedProject,
    setChatContext,
    clearChatContext,
    addChatMessage,
    clearChat,
  }
})
