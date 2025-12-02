<template>
  <div class="px-4 py-6 sm:px-0">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center">
        <router-link to="/projects" class="text-gray-500 hover:text-gray-700 mr-4">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </router-link>
        <div>
          <h2 class="text-2xl font-bold text-gray-900">{{ projectId }}</h2>
          <p class="text-sm text-gray-500">{{ pipelineStatus?.documents?.count || 0 }} documents</p>
        </div>
      </div>
      <button
        @click="refreshStatus"
        :disabled="refreshing"
        class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
      >
        <svg class="w-4 h-4 mr-2" :class="{ 'animate-spin': refreshing }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Column: Pipeline Status -->
      <div class="lg:col-span-2">
        <div class="bg-white shadow rounded-lg p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-6">Pipeline Status</h3>

          <!-- Pipeline Steps -->
          <div class="space-y-4">
            <!-- Step 1: Documents -->
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <div :class="[
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  pipelineStatus?.documents?.has_documents ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
                ]">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
              </div>
              <div class="ml-4 flex-1">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="text-sm font-medium text-gray-900">1. Documents</h4>
                    <p class="text-sm text-gray-500">{{ pipelineStatus?.documents?.count || 0 }} files uploaded</p>
                  </div>
                  <span v-if="pipelineStatus?.documents?.has_documents" class="text-green-600 text-sm font-medium">Ready</span>
                  <span v-else class="text-gray-400 text-sm">Pending</span>
                </div>
              </div>
            </div>

            <!-- Step 2: Extraction -->
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <div :class="[
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  pipelineStatus?.extraction?.is_processed ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
                ]">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <div class="ml-4 flex-1">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="text-sm font-medium text-gray-900">2. Extraction</h4>
                    <p class="text-sm text-gray-500">{{ pipelineStatus?.extraction?.count || 0 }} documents processed</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      v-if="pipelineStatus?.documents?.has_documents && !pipelineStatus?.extraction?.is_processed"
                      @click="runStage('process')"
                      :disabled="runningStage === 'process'"
                      class="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 disabled:opacity-50"
                    >
                      {{ runningStage === 'process' ? 'Running...' : 'Run' }}
                    </button>
                    <span v-if="pipelineStatus?.extraction?.is_processed" class="text-green-600 text-sm font-medium">Complete</span>
                    <button
                      v-if="pipelineStatus?.extraction?.is_processed"
                      @click="runStage('process', { force: true })"
                      :disabled="runningStage === 'process'"
                      class="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50"
                      title="Force re-extraction of all documents"
                    >
                      {{ runningStage === 'process' ? 'Running...' : 'Re-run' }}
                    </button>
                    <span v-else-if="!pipelineStatus?.documents?.has_documents" class="text-gray-400 text-sm">Pending</span>
                  </div>
                </div>
                <!-- Progress bar for extraction -->
                <div v-if="runningStage === 'process' && taskProgress.total > 0" class="mt-2">
                  <div class="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>{{ taskProgress.message || 'Processing...' }}</span>
                    <span>{{ taskProgress.current }}/{{ taskProgress.total }}</span>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-2">
                    <div
                      class="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                      :style="{ width: taskProgress.percent + '%' }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Step 3: Chunking -->
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <div :class="[
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  pipelineStatus?.chunking?.is_chunked ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
                ]">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                </div>
              </div>
              <div class="ml-4 flex-1">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="text-sm font-medium text-gray-900">3. Chunking</h4>
                    <p class="text-sm text-gray-500">{{ pipelineStatus?.chunking?.count || 0 }} chunks created</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      v-if="pipelineStatus?.extraction?.is_processed && !pipelineStatus?.chunking?.is_chunked"
                      @click="runStage('chunk')"
                      :disabled="runningStage === 'chunk'"
                      class="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 disabled:opacity-50"
                    >
                      {{ runningStage === 'chunk' ? 'Running...' : 'Run' }}
                    </button>
                    <span v-if="pipelineStatus?.chunking?.is_chunked" class="text-green-600 text-sm font-medium">Complete</span>
                    <span v-else-if="!pipelineStatus?.extraction?.is_processed" class="text-gray-400 text-sm">Pending</span>
                  </div>
                </div>
                <!-- Progress bar for chunking -->
                <div v-if="runningStage === 'chunk' && taskProgress.total > 0" class="mt-2">
                  <div class="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>{{ taskProgress.message || 'Processing...' }}</span>
                    <span>{{ taskProgress.current }}/{{ taskProgress.total }}</span>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-indigo-600 h-2 rounded-full transition-all duration-300" :style="{ width: taskProgress.percent + '%' }"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Step 4: Embedding -->
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <div :class="[
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  pipelineStatus?.embedding?.is_embedded ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
                ]">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
              </div>
              <div class="ml-4 flex-1">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="text-sm font-medium text-gray-900">4. Embedding</h4>
                    <p class="text-sm text-gray-500">{{ pipelineStatus?.embedding?.count || 0 }} embeddings generated</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      v-if="pipelineStatus?.chunking?.is_chunked && !pipelineStatus?.embedding?.is_embedded"
                      @click="runStage('embed')"
                      :disabled="runningStage === 'embed'"
                      class="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 disabled:opacity-50"
                    >
                      {{ runningStage === 'embed' ? 'Running...' : 'Run' }}
                    </button>
                    <span v-if="pipelineStatus?.embedding?.is_embedded" class="text-green-600 text-sm font-medium">Complete</span>
                    <span v-else-if="!pipelineStatus?.chunking?.is_chunked" class="text-gray-400 text-sm">Pending</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Step 5: Indexing -->
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <div :class="[
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  pipelineStatus?.index?.is_indexed ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
                ]">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </div>
              <div class="ml-4 flex-1">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="text-sm font-medium text-gray-900">5. Search Index</h4>
                    <p class="text-sm text-gray-500">Azure AI Search index</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      v-if="pipelineStatus?.embedding?.is_embedded && !pipelineStatus?.index?.is_indexed"
                      @click="runIndexPipeline()"
                      :disabled="runningStage !== null"
                      class="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 disabled:opacity-50"
                    >
                      {{ runningStage === 'index_create' || runningStage === 'index_upload' ? 'Running...' : 'Run' }}
                    </button>
                    <span v-if="pipelineStatus?.index?.is_indexed" class="text-green-600 text-sm font-medium">Indexed</span>
                    <span v-else-if="!pipelineStatus?.embedding?.is_embedded" class="text-gray-400 text-sm">Pending</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Step 6: Agent -->
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <div :class="[
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  pipelineStatus?.agent?.has_agent ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
                ]">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <div class="ml-4 flex-1">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="text-sm font-medium text-gray-900">6. Knowledge Agent</h4>
                    <p class="text-sm text-gray-500">Ready for queries</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      v-if="pipelineStatus?.index?.is_indexed && !pipelineStatus?.agent?.has_agent"
                      @click="runAgentPipeline()"
                      :disabled="runningStage !== null"
                      class="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 disabled:opacity-50"
                    >
                      {{ runningStage === 'source_create' || runningStage === 'agent_create' ? 'Running...' : 'Run' }}
                    </button>
                    <span v-if="pipelineStatus?.agent?.has_agent" class="text-green-600 text-sm font-medium">Active</span>
                    <span v-else-if="!pipelineStatus?.index?.is_indexed" class="text-gray-400 text-sm">Pending</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Pipeline Error -->
          <div v-if="pipelineError" class="mt-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
            {{ pipelineError }}
          </div>

          <!-- Quick Actions -->
          <div class="mt-8 pt-6 border-t border-gray-200">
            <div class="flex flex-wrap gap-3">
              <router-link
                :to="`/projects/${projectId}/workflow`"
                class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
              >
                Configure Workflows
              </router-link>
              <router-link
                v-if="pipelineStatus?.ready_for_query"
                to="/query"
                class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Query Documents
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: File Management -->
      <div class="lg:col-span-1">
        <div class="bg-white shadow rounded-lg p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium text-gray-900">Documents</h3>
            <label class="cursor-pointer inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200">
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Upload
              <input type="file" class="hidden" multiple @change="handleFileUpload" :disabled="uploading" />
            </label>
          </div>

          <!-- Upload Progress -->
          <div v-if="uploading" class="mb-4 p-3 bg-indigo-50 rounded-md">
            <div class="flex items-center">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600 mr-2"></div>
              <span class="text-sm text-indigo-700">Uploading...</span>
            </div>
          </div>

          <!-- Error Message -->
          <div v-if="uploadError" class="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
            {{ uploadError }}
          </div>

          <!-- Files List -->
          <div v-if="loadingFiles" class="text-center py-4">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600 mx-auto"></div>
          </div>
          <div v-else-if="files.length === 0" class="text-center py-8 text-gray-500">
            <svg class="mx-auto h-10 w-10 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="mt-2 text-sm">No documents uploaded</p>
          </div>
          <ul v-else class="divide-y divide-gray-200 max-h-96 overflow-y-auto">
            <li v-for="file in files" :key="file.path" class="py-3 flex items-center justify-between">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">{{ file.name }}</p>
                <p class="text-xs text-gray-500">{{ formatFileSize(file.size) }}</p>
              </div>
              <button
                @click="deleteFile(file.name)"
                class="ml-2 text-gray-400 hover:text-red-500"
                title="Delete file"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'
import api from '../services/api'

const route = useRoute()
const appStore = useAppStore()

const projectId = computed(() => route.params.projectId)

const pipelineStatus = ref(null)
const files = ref([])
const loadingFiles = ref(false)
const refreshing = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const runningStage = ref(null)
const pipelineError = ref('')
const taskProgress = ref({ current: 0, total: 0, percent: 0, message: '' })

onMounted(async () => {
  appStore.setSelectedProject(projectId.value)
  await Promise.all([loadStatus(), loadFiles()])
})

const loadStatus = async () => {
  try {
    pipelineStatus.value = await api.getProjectStatus(projectId.value)
  } catch (error) {
    console.error('Failed to load pipeline status:', error)
  }
}

const loadFiles = async () => {
  loadingFiles.value = true
  try {
    const data = await api.getProjectFiles(projectId.value)
    files.value = data.files || []
  } catch (error) {
    console.error('Failed to load files:', error)
  } finally {
    loadingFiles.value = false
  }
}

const refreshStatus = async () => {
  refreshing.value = true
  try {
    await Promise.all([loadStatus(), loadFiles()])
  } finally {
    refreshing.value = false
  }
}

const handleFileUpload = async (event) => {
  const selectedFiles = event.target.files
  if (!selectedFiles.length) return

  uploading.value = true
  uploadError.value = ''

  try {
    for (const file of selectedFiles) {
      await api.uploadProjectFile(projectId.value, file)
    }
    await Promise.all([loadStatus(), loadFiles()])
  } catch (error) {
    uploadError.value = error.response?.data?.detail || 'Failed to upload files'
  } finally {
    uploading.value = false
    event.target.value = '' // Reset input
  }
}

const deleteFile = async (filename) => {
  if (!confirm(`Delete ${filename}?`)) return

  try {
    await api.deleteProjectFile(projectId.value, filename)
    await Promise.all([loadStatus(), loadFiles()])
  } catch (error) {
    console.error('Failed to delete file:', error)
  }
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const runStage = async (stage, options = {}) => {
  runningStage.value = stage
  pipelineError.value = ''
  taskProgress.value = { current: 0, total: 0, percent: 0, message: 'Starting...' }

  try {
    const result = await api.runPipelineStage(projectId.value, stage, options)
    console.log('Pipeline stage started:', result)

    // Poll for status updates
    const taskId = result.task_id
    let attempts = 0
    const maxAttempts = 600 // 10 minutes max for long extractions

    return new Promise((resolve, reject) => {
      const pollStatus = setInterval(async () => {
        attempts++
        try {
          const taskStatus = await api.getTaskStatus(taskId)

          // Update progress
          if (taskStatus.progress) {
            taskProgress.value = {
              current: taskStatus.progress.current || 0,
              total: taskStatus.progress.total || 0,
              percent: taskStatus.progress.percent || 0,
              message: taskStatus.progress.message || ''
            }
          }

          if (taskStatus.status === 'completed') {
            clearInterval(pollStatus)
            taskProgress.value = { current: 0, total: 0, percent: 0, message: '' }
            await loadStatus()
            resolve()
          } else if (taskStatus.status === 'failed') {
            clearInterval(pollStatus)
            taskProgress.value = { current: 0, total: 0, percent: 0, message: '' }
            pipelineError.value = taskStatus.error || 'Pipeline stage failed'
            await loadStatus()
            reject(new Error(taskStatus.error || 'Pipeline stage failed'))
          } else if (attempts >= maxAttempts) {
            clearInterval(pollStatus)
            taskProgress.value = { current: 0, total: 0, percent: 0, message: '' }
            pipelineError.value = 'Pipeline stage timed out'
            reject(new Error('Pipeline stage timed out'))
          }
        } catch (error) {
          console.error('Error polling task status:', error)
        }
      }, 1000)
    })

  } catch (error) {
    taskProgress.value = { current: 0, total: 0, percent: 0, message: '' }
    pipelineError.value = error.response?.data?.detail || 'Failed to start pipeline stage'
    throw error
  }
}

// Run index creation and upload sequentially
const runIndexPipeline = async () => {
  pipelineError.value = ''
  try {
    // Step 1: Create the index
    await runStage('index_create')
    // Step 2: Upload documents to the index
    await runStage('index_upload')
  } catch (error) {
    console.error('Index pipeline failed:', error)
  } finally {
    runningStage.value = null
  }
}

// Run knowledge source and agent creation sequentially
const runAgentPipeline = async () => {
  pipelineError.value = ''
  try {
    // Step 1: Create knowledge source
    await runStage('source_create')
    // Step 2: Create knowledge agent
    await runStage('agent_create')
  } catch (error) {
    console.error('Agent pipeline failed:', error)
  } finally {
    runningStage.value = null
  }
}
</script>
