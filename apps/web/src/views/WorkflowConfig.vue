<template>
  <div class="px-4 py-6 sm:px-0">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center">
        <router-link :to="`/projects/${projectId}`" class="text-gray-500 hover:text-gray-700 mr-4">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </router-link>
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Workflow Configuration</h2>
          <p class="text-sm text-gray-500">Project: {{ projectId }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="exportWorkflow"
          class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          title="Export workflow as JSON"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export
        </button>
        <label class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 cursor-pointer" title="Import workflow from JSON">
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Import
          <input
            type="file"
            accept=".json"
            @change="importWorkflow"
            class="hidden"
          />
        </label>
        <button
          @click="showAddSectionModal = true"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
        >
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Add Section
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      <p class="mt-2 text-gray-500">Loading sections...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="sections.length === 0" class="text-center py-12 bg-white rounded-lg shadow">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900">No sections configured</h3>
      <p class="mt-1 text-sm text-gray-500">Add sections to define your workflow questions.</p>
      <button
        @click="showAddSectionModal = true"
        class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
      >
        Add Section
      </button>
    </div>

    <!-- Sections List -->
    <div v-else class="space-y-6">
      <div
        v-for="section in sections"
        :key="section.id"
        class="bg-white shadow rounded-lg overflow-hidden"
      >
        <!-- Section Header -->
        <div class="bg-gray-50 px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <button
                @click="toggleSection(section.id)"
                class="mr-3 text-gray-400 hover:text-gray-600"
              >
                <svg
                  :class="['w-5 h-5 transition-transform', expandedSections[section.id] ? 'rotate-90' : '']"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
              <div>
                <h3 class="text-lg font-medium text-gray-900">{{ section.name }}</h3>
                <p class="text-sm text-gray-500">{{ section.questions?.length || 0 }} questions</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="editSection(section)"
                class="text-gray-400 hover:text-indigo-600"
                title="Edit section"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                @click="confirmDeleteSection(section)"
                class="text-gray-400 hover:text-red-600"
                title="Delete section"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Questions List (Collapsible) -->
        <div v-if="expandedSections[section.id]" class="p-6">
          <!-- Add Question Button -->
          <button
            @click="addQuestion(section)"
            class="mb-4 inline-flex items-center px-3 py-1.5 border border-dashed border-gray-300 text-sm font-medium rounded-md text-gray-600 hover:border-indigo-500 hover:text-indigo-600"
          >
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Question
          </button>

          <!-- Questions -->
          <div v-if="section.questions?.length > 0" class="space-y-3">
            <div
              v-for="(question, idx) in sortedQuestions(section.questions)"
              :key="question.id"
              class="p-4 bg-gray-50 rounded-lg"
            >
              <div class="flex items-start justify-between">
                <!-- Order controls -->
                <div class="flex flex-col items-center mr-3">
                  <button
                    @click="moveQuestion(section, question, 'up')"
                    :disabled="idx === 0"
                    class="p-1 text-gray-400 hover:text-indigo-600 disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Move up"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                    </svg>
                  </button>
                  <span class="text-xs font-medium text-white bg-indigo-500 px-2 py-0.5 rounded my-1">{{ idx + 1 }}</span>
                  <button
                    @click="moveQuestion(section, question, 'down')"
                    :disabled="idx === sortedQuestions(section.questions).length - 1"
                    class="p-1 text-gray-400 hover:text-indigo-600 disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Move down"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                </div>
                <div class="flex-1">
                  <p class="text-sm text-gray-900 font-medium">{{ question.question }}</p>
                  <p v-if="question.instructions" class="mt-1 text-xs text-gray-500 italic line-clamp-2">{{ question.instructions }}</p>
                </div>
                <div class="flex items-center gap-1 ml-4">
                  <button
                    @click="editQuestion(section, question)"
                    class="text-gray-400 hover:text-indigo-600"
                    title="Edit question"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    @click="confirmDeleteQuestion(section, question)"
                    class="text-gray-400 hover:text-red-600"
                    title="Delete question"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-6 text-gray-500 text-sm">
            No questions in this section
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Section Modal -->
    <div v-if="showSectionModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="closeSectionModal"></div>
        <div class="relative bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            {{ editingSectionId ? 'Edit Section' : 'Add Section' }}
          </h3>
          <form @submit.prevent="saveSection">
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Section ID</label>
                <input
                  v-model="sectionForm.id"
                  type="text"
                  required
                  :disabled="!!editingSectionId"
                  pattern="[a-zA-Z0-9_-]+"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white text-gray-900 disabled:bg-gray-100 disabled:text-gray-500"
                  placeholder="section-1"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Section Name</label>
                <input
                  v-model="sectionForm.name"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white text-gray-900"
                  placeholder="General Requirements"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Template (Instructions for all questions)</label>
                <textarea
                  v-model="sectionForm.template"
                  rows="6"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white text-gray-900"
                  placeholder="You are an assistant helping answer questions about documents..."
                ></textarea>
              </div>
            </div>
            <div v-if="sectionError" class="mt-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
              {{ sectionError }}
            </div>
            <div class="mt-6 flex justify-end gap-3">
              <button
                type="button"
                @click="closeSectionModal"
                class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="savingSection"
                class="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              >
                {{ savingSection ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Add/Edit Question Modal -->
    <div v-if="showQuestionModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="closeQuestionModal"></div>
        <div class="relative bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            {{ editingQuestionId ? 'Edit Question' : 'Add Question' }}
          </h3>
          <form @submit.prevent="saveQuestion">
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Question</label>
                <textarea
                  v-model="questionForm.question"
                  rows="3"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white text-gray-900"
                  placeholder="What is the required voltage rating?"
                ></textarea>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Instructions (Optional)</label>
                <textarea
                  v-model="questionForm.instructions"
                  rows="3"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white text-gray-900"
                  placeholder="Look for specifications in the technical requirements section..."
                ></textarea>
              </div>
            </div>
            <div v-if="questionError" class="mt-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
              {{ questionError }}
            </div>
            <div class="mt-6 flex justify-end gap-3">
              <button
                type="button"
                @click="closeQuestionModal"
                class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="savingQuestion"
                class="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              >
                {{ savingQuestion ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="showDeleteModal = false"></div>
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Confirm Delete</h3>
          <p class="text-sm text-gray-500 mb-4">{{ deleteMessage }}</p>
          <div class="flex justify-end gap-3">
            <button
              type="button"
              @click="showDeleteModal = false"
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              @click="executeDelete"
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'
import api from '../services/api'

const route = useRoute()
const appStore = useAppStore()

const projectId = computed(() => route.params.projectId)

const sections = ref([])
const loading = ref(false)
const expandedSections = reactive({})

// Section modal state
const showSectionModal = ref(false)
const showAddSectionModal = ref(false)
const editingSectionId = ref(null)
const sectionForm = reactive({ id: '', name: '', template: '' })
const sectionError = ref('')
const savingSection = ref(false)

// Question modal state
const showQuestionModal = ref(false)
const editingQuestionId = ref(null)
const editingSectionForQuestion = ref(null)
const questionForm = reactive({ question: '', instructions: '' })
const questionError = ref('')
const savingQuestion = ref(false)

// Delete modal state
const showDeleteModal = ref(false)
const deleteMessage = ref('')
const deleteCallback = ref(null)
const deleting = ref(false)

// Watch for showAddSectionModal to open the actual modal
const openAddSectionModal = () => {
  editingSectionId.value = null
  sectionForm.id = ''
  sectionForm.name = ''
  sectionForm.template = ''
  sectionError.value = ''
  showSectionModal.value = true
  showAddSectionModal.value = false
}

// Use a watcher effect
if (showAddSectionModal.value) {
  openAddSectionModal()
}

onMounted(async () => {
  appStore.setSelectedProject(projectId.value)
  await loadSections()

  // Check if we need to open add section modal
  if (showAddSectionModal.value) {
    openAddSectionModal()
  }
})

// Handle showAddSectionModal changes
const handleShowAddSection = () => {
  if (showAddSectionModal.value) {
    openAddSectionModal()
  }
}

// Watch for changes
import { watch } from 'vue'
watch(showAddSectionModal, handleShowAddSection)

const loadSections = async () => {
  loading.value = true
  try {
    const data = await api.getSections(projectId.value)
    sections.value = data
  } catch (error) {
    console.error('Failed to load sections:', error)
    sections.value = []
  } finally {
    loading.value = false
  }
}

const toggleSection = (sectionId) => {
  expandedSections[sectionId] = !expandedSections[sectionId]
}

// Sort questions by order
const sortedQuestions = (questions) => {
  if (!questions) return []
  return [...questions].sort((a, b) => (a.order || 999) - (b.order || 999))
}

// Section CRUD
const editSection = (section) => {
  editingSectionId.value = section.id
  sectionForm.id = section.id
  sectionForm.name = section.name
  sectionForm.template = section.template || ''
  sectionError.value = ''
  showSectionModal.value = true
}

const closeSectionModal = () => {
  showSectionModal.value = false
  editingSectionId.value = null
}

const saveSection = async () => {
  savingSection.value = true
  sectionError.value = ''
  try {
    if (editingSectionId.value) {
      await api.updateSection(projectId.value, editingSectionId.value, {
        name: sectionForm.name,
        template: sectionForm.template
      })
    } else {
      await api.createSection(projectId.value, {
        id: sectionForm.id,
        name: sectionForm.name,
        template: sectionForm.template
      })
    }
    closeSectionModal()
    await loadSections()
  } catch (error) {
    sectionError.value = error.response?.data?.detail || 'Failed to save section'
  } finally {
    savingSection.value = false
  }
}

const confirmDeleteSection = (section) => {
  deleteMessage.value = `Are you sure you want to delete section "${section.name}"? This will also delete all ${section.questions?.length || 0} questions.`
  deleteCallback.value = async () => {
    await api.deleteSection(projectId.value, section.id)
    await loadSections()
  }
  showDeleteModal.value = true
}

// Question CRUD
const addQuestion = (section) => {
  editingSectionForQuestion.value = section
  editingQuestionId.value = null
  questionForm.question = ''
  questionForm.instructions = ''
  questionError.value = ''
  showQuestionModal.value = true
}

const editQuestion = (section, question) => {
  editingSectionForQuestion.value = section
  editingQuestionId.value = question.id
  questionForm.question = question.question
  questionForm.instructions = question.instructions || ''
  questionError.value = ''
  showQuestionModal.value = true
}

const closeQuestionModal = () => {
  showQuestionModal.value = false
  editingQuestionId.value = null
  editingSectionForQuestion.value = null
}

const saveQuestion = async () => {
  savingQuestion.value = true
  questionError.value = ''
  try {
    const sectionId = editingSectionForQuestion.value.id
    if (editingQuestionId.value) {
      // Update existing question (don't change order)
      await api.updateQuestion(projectId.value, sectionId, editingQuestionId.value, {
        question: questionForm.question,
        instructions: questionForm.instructions
      })
    } else {
      // Create new question - add at end
      const section = editingSectionForQuestion.value
      const maxOrder = section.questions?.reduce((max, q) => Math.max(max, q.order || 0), 0) || 0
      const newOrder = maxOrder + 1
      const questionId = `q${Date.now()}`  // Use timestamp for unique ID
      await api.createQuestion(projectId.value, sectionId, {
        id: questionId,
        order: newOrder,
        question: questionForm.question,
        instructions: questionForm.instructions
      })
    }
    closeQuestionModal()
    await loadSections()
  } catch (error) {
    questionError.value = error.response?.data?.detail || 'Failed to save question'
  } finally {
    savingQuestion.value = false
  }
}

const confirmDeleteQuestion = (section, question) => {
  deleteMessage.value = `Are you sure you want to delete question "${question.question}"?`
  deleteCallback.value = async () => {
    await api.deleteQuestion(projectId.value, section.id, question.id)
    await loadSections()
  }
  showDeleteModal.value = true
}

// Move question up or down
const moveQuestion = async (section, question, direction) => {
  const sorted = sortedQuestions(section.questions)
  const currentIndex = sorted.findIndex(q => q.id === question.id)

  if (direction === 'up' && currentIndex > 0) {
    // Swap with previous question
    const prevQuestion = sorted[currentIndex - 1]
    const currentOrder = question.order || currentIndex + 1
    const prevOrder = prevQuestion.order || currentIndex

    // Update both questions with swapped orders
    try {
      await api.updateQuestion(projectId.value, section.id, question.id, { order: prevOrder })
      await api.updateQuestion(projectId.value, section.id, prevQuestion.id, { order: currentOrder })
      await loadSections()
    } catch (error) {
      console.error('Failed to move question:', error)
    }
  } else if (direction === 'down' && currentIndex < sorted.length - 1) {
    // Swap with next question
    const nextQuestion = sorted[currentIndex + 1]
    const currentOrder = question.order || currentIndex + 1
    const nextOrder = nextQuestion.order || currentIndex + 2

    // Update both questions with swapped orders
    try {
      await api.updateQuestion(projectId.value, section.id, question.id, { order: nextOrder })
      await api.updateQuestion(projectId.value, section.id, nextQuestion.id, { order: currentOrder })
      await loadSections()
    } catch (error) {
      console.error('Failed to move question:', error)
    }
  }
}

// Execute delete
const executeDelete = async () => {
  if (!deleteCallback.value) return
  deleting.value = true
  try {
    await deleteCallback.value()
    showDeleteModal.value = false
  } catch (error) {
    console.error('Delete failed:', error)
  } finally {
    deleting.value = false
    deleteCallback.value = null
  }
}

// Export workflow as JSON
const exportWorkflow = async () => {
  try {
    const workflow = await api.exportWorkflow(projectId.value)
    const blob = new Blob([JSON.stringify(workflow, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${projectId.value}_workflow.json`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    console.error('Failed to export workflow:', error)
    alert(`Failed to export workflow: ${error.response?.data?.detail || error.message}`)
  }
}

// Import workflow from JSON file
const importWorkflow = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    const text = await file.text()
    const workflow = JSON.parse(text)

    // Confirm import (will replace existing workflow)
    const sectionCount = workflow.sections?.length || 0
    const questionCount = workflow.sections?.reduce((sum, s) => sum + (s.questions?.length || 0), 0) || 0

    if (!confirm(`Import workflow with ${sectionCount} sections and ${questionCount} questions? This will replace the current workflow configuration.`)) {
      return
    }

    await api.importWorkflow(projectId.value, workflow)
    await loadSections()
    alert('Workflow imported successfully!')
  } catch (error) {
    console.error('Failed to import workflow:', error)
    if (error instanceof SyntaxError) {
      alert('Invalid JSON file. Please select a valid workflow JSON file.')
    } else {
      alert(`Failed to import workflow: ${error.response?.data?.detail || error.message}`)
    }
  } finally {
    // Reset file input
    if (event.target) {
      event.target.value = ''
    }
  }
}
</script>
