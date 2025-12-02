<template>
  <div class="px-4 py-6 sm:px-0">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900">Projects</h2>
      <button
        @click="showCreateModal = true"
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        New Project
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      <p class="mt-2 text-gray-500">Loading projects...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="projects.length === 0" class="text-center py-12 bg-white rounded-lg shadow">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900">No projects</h3>
      <p class="mt-1 text-sm text-gray-500">Get started by creating a new project.</p>
      <button
        @click="showCreateModal = true"
        class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
      >
        Create Project
      </button>
    </div>

    <!-- Projects Grid -->
    <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="project in projects"
        :key="project.name"
        class="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow cursor-pointer"
        @click="openProject(project.name)"
      >
        <div class="p-5">
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="h-12 w-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <span class="text-indigo-600 font-bold text-lg">{{ project.name.substring(0, 2).toUpperCase() }}</span>
                </div>
              </div>
              <div class="ml-4">
                <h3 class="text-lg font-medium text-gray-900">{{ project.name }}</h3>
                <p class="text-sm text-gray-500">{{ project.document_count }} documents</p>
              </div>
            </div>
            <button
              @click.stop="confirmDelete(project)"
              class="text-gray-400 hover:text-red-500 transition-colors"
              title="Delete project"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
          <div class="mt-4">
            <div class="flex flex-wrap gap-2">
              <span
                v-if="project.has_extraction_results"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
              >
                Extracted
              </span>
              <span
                v-if="project.has_chunked_documents"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                Chunked
              </span>
              <span
                v-if="project.has_embedded_documents"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800"
              >
                Embedded
              </span>
              <span
                v-if="project.has_results_csv"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800"
              >
                Results
              </span>
              <span
                v-if="!project.has_extraction_results && !project.has_chunked_documents && !project.has_embedded_documents"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
              >
                Not processed
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="showCreateModal = false"></div>
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Create New Project</h3>
          <form @submit.prevent="createProject">
            <div class="mb-4">
              <label for="projectName" class="block text-sm font-medium text-gray-700 mb-1">Project Name</label>
              <input
                id="projectName"
                v-model="newProjectName"
                type="text"
                required
                pattern="[a-zA-Z0-9_-]+"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="my-project"
              />
              <p class="mt-1 text-xs text-gray-500">Only letters, numbers, underscores, and hyphens allowed.</p>
            </div>
            <div v-if="createError" class="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
              {{ createError }}
            </div>
            <div class="flex justify-end gap-3">
              <button
                type="button"
                @click="showCreateModal = false"
                class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="creating"
                class="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              >
                {{ creating ? 'Creating...' : 'Create' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="showDeleteModal = false"></div>
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Delete Project</h3>
          <p class="text-sm text-gray-500 mb-4">
            Are you sure you want to delete <strong>{{ projectToDelete?.name }}</strong>?
            This will permanently remove all documents and results. This action cannot be undone.
          </p>
          <div v-if="deleteError" class="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
            {{ deleteError }}
          </div>
          <div class="flex justify-end gap-3">
            <button
              type="button"
              @click="showDeleteModal = false"
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              @click="deleteProject"
              :disabled="deleting"
              class="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
            >
              {{ deleting ? 'Deleting...' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { storeToRefs } from 'pinia'
import api from '../services/api'

const router = useRouter()
const appStore = useAppStore()
const { projects } = storeToRefs(appStore)

const loading = ref(false)
const showCreateModal = ref(false)
const showDeleteModal = ref(false)
const newProjectName = ref('')
const creating = ref(false)
const createError = ref('')
const projectToDelete = ref(null)
const deleting = ref(false)
const deleteError = ref('')

onMounted(async () => {
  await loadProjects()
})

const loadProjects = async () => {
  loading.value = true
  try {
    await appStore.loadProjects()
  } finally {
    loading.value = false
  }
}

const openProject = (projectName) => {
  appStore.setSelectedProject(projectName)
  router.push(`/projects/${projectName}`)
}

const createProject = async () => {
  creating.value = true
  createError.value = ''
  try {
    await api.createProject(newProjectName.value)
    showCreateModal.value = false
    newProjectName.value = ''
    await loadProjects()
  } catch (error) {
    createError.value = error.response?.data?.detail || 'Failed to create project'
  } finally {
    creating.value = false
  }
}

const confirmDelete = (project) => {
  projectToDelete.value = project
  deleteError.value = ''
  showDeleteModal.value = true
}

const deleteProject = async () => {
  if (!projectToDelete.value) return

  deleting.value = true
  deleteError.value = ''
  try {
    await api.deleteProject(projectToDelete.value.name)
    showDeleteModal.value = false
    projectToDelete.value = null
    await loadProjects()
  } catch (error) {
    deleteError.value = error.response?.data?.detail || 'Failed to delete project'
  } finally {
    deleting.value = false
  }
}
</script>
