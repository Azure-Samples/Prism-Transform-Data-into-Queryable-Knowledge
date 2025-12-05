<template>
  <div class="px-4 py-6 sm:px-0">
    <h2 class="text-2xl font-bold text-gray-900 mb-6">Sections</h2>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="text-gray-500">Loading sections...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <p class="text-red-800">{{ error }}</p>
    </div>

    <!-- Sections Table -->
    <div v-else class="bg-white shadow rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20">
              Section
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Name
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
              Questions
            </th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-64">
              Actions
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="section in sections" :key="section.section_id" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
              {{ section.section_id }}
            </td>
            <td class="px-6 py-4 text-sm text-gray-900">
              {{ section.section_name }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ section.question_count }} questions
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button
                @click="exportQuestions(section.section_id)"
                class="text-green-600 hover:text-green-900 mr-3"
                title="Export questions as CSV"
              >
                Export CSV
              </button>
              <label class="text-blue-600 hover:text-blue-900 mr-3 cursor-pointer" title="Import questions from CSV">
                Import CSV
                <input
                  type="file"
                  accept=".csv"
                  @change="importQuestions($event, section.section_id)"
                  class="hidden"
                />
              </label>
              <button
                @click="editQuestions(section.section_id)"
                class="text-indigo-600 hover:text-indigo-900 mr-3"
              >
                Edit
              </button>
              <button
                v-if="section.completed_count > 0"
                @click="clearAnswers(section.section_id)"
                class="text-red-600 hover:text-red-900 mr-3"
                title="Clear all answers for this section"
              >
                Clear
              </button>
              <button
                @click="runSection(section.section_id)"
                :disabled="runningSection === section.section_id"
                class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ runningSection === section.section_id ? 'Running...' : 'Run' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Active Task Status -->
    <div v-if="activeTask" class="mt-8 bg-white shadow rounded-lg p-6">
      <h3 class="text-lg font-medium text-gray-900 mb-4">
        Running Section {{ activeTask.section_id }}
      </h3>
      <div class="space-y-4">
        <div>
          <div class="flex justify-between text-sm text-gray-600 mb-2">
            <span>Status: {{ activeTask.status }}</span>
            <span v-if="activeTask.questions_total > 0">
              {{ activeTask.questions_completed }} / {{ activeTask.questions_total }} completed
            </span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-600 h-2 rounded-full transition-all duration-300"
              :style="{ width: `${taskProgress}%` }"
            ></div>
          </div>
        </div>
        <div v-if="activeTask.current_question" class="text-sm text-gray-600">
          Current: {{ activeTask.current_question }}
        </div>
        <div v-if="activeTask.error" class="text-sm text-red-600">
          Error: {{ activeTask.error }}
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { storeToRefs } from 'pinia'
import api from '../services/api'

const router = useRouter()

const appStore = useAppStore()
const { selectedProject: storeSelectedProject } = storeToRefs(appStore)

const sections = ref([])
const loading = ref(false)
const error = ref(null)
const runningSection = ref(null)
const activeTask = ref(null)
const pollInterval = ref(null)

// Edit questions - now redirects to workflow config page
// Modal removed - use WorkflowConfig.vue instead

const taskProgress = computed(() => {
  if (!activeTask.value || activeTask.value.questions_total === 0) return 0
  return Math.round((activeTask.value.questions_completed / activeTask.value.questions_total) * 100)
})

onMounted(async () => {
  await loadSections()
})

onUnmounted(() => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
  }
})

const loadSections = async () => {
  loading.value = true
  error.value = null
  try {
    sections.value = await api.getWorkflows(storeSelectedProject.value)
  } catch (err) {
    console.error('Failed to load workflows:', err)
    error.value = 'Failed to load sections. Make sure the backend is running.'
  } finally {
    loading.value = false
  }
}

const runSection = async (sectionId) => {
  try {
    runningSection.value = sectionId
    const response = await api.runWorkflow(sectionId, storeSelectedProject.value)

    activeTask.value = {
      task_id: response.task_id,
      section_id: sectionId,
      status: response.status,
      questions_completed: 0,
      questions_total: 0,
      current_question: null,
      error: null,
    }

    startPolling(sectionId, response.task_id)
  } catch (err) {
    console.error('Failed to run workflow:', err)
    error.value = `Failed to run section ${sectionId}: ${err.message}`
    runningSection.value = null
  }
}

const startPolling = (sectionId, taskId) => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
  }

  let completionHandled = false

  pollInterval.value = setInterval(async () => {
    if (completionHandled) return

    try {
      const status = await api.getWorkflowStatus(sectionId, taskId)
      activeTask.value = status

      if (status.status === 'completed' || status.status === 'failed') {
        completionHandled = true
        clearInterval(pollInterval.value)
        pollInterval.value = null
        runningSection.value = null
        await loadSections()

        // Show success message with link to results
        if (status.status === 'completed') {
          error.value = null
          // Show a success message (you can replace this with a toast notification)
          alert(`Section ${sectionId} completed! Go to Results page to view answers.`)
        }
      }
    } catch (err) {
      console.error('Failed to get workflow status:', err)
    }
  }, 3000)
}

const editQuestions = (sectionId) => {
  // Navigate to the workflow config page for editing
  router.push(`/projects/${storeSelectedProject.value}/workflow`)
}

const exportQuestions = async (sectionId) => {
  try {
    const blob = await api.exportSectionQuestions(storeSelectedProject.value, sectionId)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${storeSelectedProject.value}_section${sectionId}_questions.csv`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (err) {
    console.error('Failed to export questions:', err)
    error.value = `Failed to export questions: ${err.message}`
  }
}

const importQuestions = async (event, sectionId) => {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    await api.importSectionQuestions(storeSelectedProject.value, sectionId, file)

    // Reload sections to show updated counts
    await loadSections()

    // Show success message
    console.log(`Successfully imported questions for section ${sectionId}`)
  } catch (err) {
    console.error('Failed to import questions:', err)
    error.value = `Failed to import questions: ${err.message}`
  } finally {
    // Reset file input
    if (event.target) {
      event.target.value = ''
    }
  }
}

const clearAnswers = async (sectionId) => {
  if (!confirm(`Clear all answers for Section ${sectionId}? This cannot be undone.`)) {
    return
  }

  try {
    const result = await api.clearSectionAnswers(sectionId, storeSelectedProject.value)
    console.log(`Cleared ${result.cleared_count} answers for section ${sectionId}`)

    // Reload sections to show updated counts
    await loadSections()
  } catch (err) {
    console.error('Failed to clear answers:', err)
    error.value = `Failed to clear answers: ${err.message}`
  }
}
</script>

<style scoped>
/* Force light mode colors for form inputs to prevent browser dark mode override */
input[type="text"],
input,
textarea {
  color: #111827 !important; /* gray-900 */
  background-color: #ffffff !important; /* white */
  color-scheme: light;
}

input::placeholder,
textarea::placeholder {
  color: #9ca3af !important; /* gray-400 */
}
</style>
