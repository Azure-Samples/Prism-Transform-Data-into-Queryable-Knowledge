import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

export const useAppStore = defineStore('app', () => {
  const selectedProject = ref('')
  const projects = ref([])
  const activeIndex = ref('')

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
  }

  return {
    selectedProject,
    projects,
    activeIndex,
    loadProjects,
    loadActiveIndex,
    setSelectedProject,
  }
})
