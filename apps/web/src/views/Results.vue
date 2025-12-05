<template>
  <div class="px-4 py-6 sm:px-0">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900">Results</h2>
      <div class="flex gap-3">
        <select
          v-model="selectedSection"
          class="block pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
        >
          <option value="all">All Sections</option>
          <option v-for="section in results?.sections" :key="section.section_id" :value="section.section_id">
            Section {{ section.section_id }}: {{ section.section_name }}
          </option>
        </select>
        <button
          @click="runEvaluation"
          :disabled="!results || evaluating"
          class="inline-flex items-center px-4 py-2 border border-indigo-300 text-sm font-medium rounded-md text-indigo-700 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50"
          title="Run AI evaluation on all answers"
        >
          <svg v-if="evaluating" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ evaluating ? 'Evaluating...' : 'Run Evaluation' }}
        </button>
        <button
          @click="exportCsv"
          :disabled="!results"
          class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          Export CSV
        </button>
      </div>
    </div>

    <!-- Stats -->
    <div v-if="results" class="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-6">
      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="h-12 w-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                <span class="text-indigo-600 font-bold text-lg">{{ results.total_questions }}</span>
              </div>
            </div>
            <div class="ml-5">
              <p class="text-sm font-medium text-gray-500">Total Questions</p>
            </div>
          </div>
        </div>
      </div>
      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
                <span class="text-green-600 font-bold text-lg">{{ results.answered_questions }}</span>
              </div>
            </div>
            <div class="ml-5">
              <p class="text-sm font-medium text-gray-500">Answered</p>
            </div>
          </div>
        </div>
      </div>
      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="h-12 w-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                <span class="text-yellow-600 font-bold text-lg">{{ completionPercentage }}%</span>
              </div>
            </div>
            <div class="ml-5">
              <p class="text-sm font-medium text-gray-500">Completion</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Results Table -->
    <div v-if="filteredSections.length > 0" class="bg-white shadow overflow-hidden sm:rounded-lg">
      <div v-for="section in filteredSections" :key="section.section_id" class="border-b border-gray-200 last:border-0">
        <div class="px-4 py-5 sm:px-6 bg-gray-50">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900">
              Section {{ section.section_id }}: {{ section.section_name }}
            </h3>
            <div class="flex items-center gap-4">
              <span class="text-sm text-gray-600">
                {{ getSectionProgress(section).answered }} / {{ getSectionProgress(section).total }} answered
              </span>
              <div class="w-32">
                <div class="w-full bg-gray-200 rounded-full h-2">
                  <div
                    class="bg-indigo-600 h-2 rounded-full"
                    :style="{ width: `${getSectionProgress(section).percentage}%` }"
                  ></div>
                </div>
              </div>
              <span class="text-sm font-medium text-gray-700">
                {{ getSectionProgress(section).percentage }}%
              </span>
              <button
                v-if="getSectionProgress(section).answered > 0"
                @click="clearSectionAnswers(section.section_id)"
                class="ml-4 px-3 py-1 text-sm text-red-600 hover:text-red-900 border border-red-300 hover:border-red-400 rounded-md"
                title="Clear all answers for this section"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
        <div class="px-4 py-5 sm:p-6">
          <div class="space-y-6">
            <div
              v-for="(question, idx) in section.questions"
              :key="idx"
              class="border-l-4 pl-4"
              :class="question.answer ? 'border-green-400' : 'border-gray-300'"
            >
              <div class="flex justify-between items-start">
                <h4 class="text-sm font-medium text-gray-900 mb-2 flex-1">
                  {{ question.question_name }}
                </h4>
                <div class="flex items-center gap-2">
                  <button
                    v-if="question.answer"
                    @click="evaluateSingleQuestion(section.section_id, question.question_id)"
                    :disabled="evaluatingQuestion === `${section.section_id}/${question.question_id}`"
                    class="px-2 py-1 text-xs font-medium text-yellow-600 hover:text-yellow-800 hover:bg-yellow-50 rounded flex items-center gap-1"
                    :title="question.evaluation ? 'Re-evaluate this answer' : 'Evaluate this answer'"
                  >
                    <svg v-if="evaluatingQuestion === `${section.section_id}/${question.question_id}`" class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <svg v-else class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {{ question.evaluation ? 'Re-eval' : 'Eval' }}
                  </button>
                  <button
                    @click="openChat(section, question)"
                    class="px-2 py-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded flex items-center gap-1"
                    title="Discuss this result"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    Chat
                  </button>
                </div>
              </div>
              <!-- Evaluation Scores -->
              <div v-if="question.evaluation?.scores" class="mb-3 flex flex-wrap gap-2">
                <div
                  v-for="(score, metric) in question.evaluation.scores"
                  :key="metric"
                  :title="score.reason || metric"
                  class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                  :class="getScoreClass(score.score)"
                >
                  <span class="capitalize">{{ metric }}</span>
                  <span class="ml-1 font-bold">{{ score.score ?? '-' }}</span>
                </div>
                <div
                  v-if="question.evaluation.average_score"
                  class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                  title="Average of all scores"
                >
                  <span>Avg</span>
                  <span class="ml-1 font-bold">{{ question.evaluation.average_score }}</span>
                </div>
              </div>

              <dl class="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-3">
                <div class="sm:col-span-1">
                  <dt class="text-xs font-medium text-gray-500">Answer</dt>
                  <dd class="mt-1 text-sm text-gray-900">
                    {{ question.answer || 'Not answered' }}
                  </dd>
                </div>
                <div class="sm:col-span-1">
                  <dt class="text-xs font-medium text-gray-500">Reference</dt>
                  <dd class="mt-1 text-sm text-gray-900">
                    {{ question.reference || 'N/A' }}
                  </dd>
                </div>
                <div class="sm:col-span-1">
                  <dt class="text-xs font-medium text-gray-500">Comments</dt>
                  <dd class="mt-1 text-sm text-gray-900">
                    {{ question.comments || 'N/A' }}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!loading" class="text-center py-12 bg-white shadow rounded-lg">
      <p class="text-gray-500">No results available. Run workflows first.</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <p class="text-gray-500">Loading results...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { storeToRefs } from 'pinia'
import api from '../services/api'

const router = useRouter()
const appStore = useAppStore()
const { selectedProject } = storeToRefs(appStore)

const results = ref(null)
const selectedSection = ref('all')
const loading = ref(false)
const evaluating = ref(false)
const evaluatingQuestion = ref(null)

const completionPercentage = computed(() => {
  if (!results.value || results.value.total_questions === 0) return 0
  return Math.round((results.value.answered_questions / results.value.total_questions) * 100)
})

const filteredSections = computed(() => {
  if (!results.value) return []
  if (selectedSection.value === 'all') return results.value.sections
  return results.value.sections.filter(s => s.section_id === selectedSection.value)
})

onMounted(async () => {
  await loadResults()
})

// Watch for project changes and reload results
watch(selectedProject, async () => {
  await loadResults()
})

const getSectionProgress = (section) => {
  const answered = section.questions.filter(q => q.answer && q.answer.trim() !== '').length
  const total = section.questions.length
  const percentage = total > 0 ? Math.round((answered / total) * 100) : 0
  return { answered, total, percentage }
}

const loadResults = async () => {
  loading.value = true
  results.value = null
  try {
    results.value = await api.getResults(selectedProject.value)
  } catch (error) {
    console.error('Failed to load results:', error)
    results.value = null
  } finally {
    loading.value = false
  }
}

const exportCsv = async () => {
  try {
    const blob = await api.exportResults(selectedProject.value)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedProject.value}_results.csv`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    console.error('Failed to export results:', error)
  }
}

const clearSectionAnswers = async (sectionId) => {
  if (!confirm(`Clear all answers for Section ${sectionId}? This cannot be undone.`)) {
    return
  }

  try {
    const result = await api.clearSectionAnswers(sectionId, selectedProject.value)
    console.log(`Cleared ${result.cleared_count} answers for section ${sectionId}`)

    // Reload results to show updated data
    await loadResults()
  } catch (error) {
    console.error('Failed to clear answers:', error)
    alert(`Failed to clear answers: ${error.message}`)
  }
}

const runEvaluation = async () => {
  if (!confirm('Run AI evaluation on all answered questions? This may take a few minutes.')) {
    return
  }

  evaluating.value = true

  try {
    const result = await api.runEvaluation(selectedProject.value)
    console.log('Evaluation complete:', result)

    // Show summary
    const avgScores = result.average_scores || {}
    const scoreText = Object.entries(avgScores)
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ')

    alert(`Evaluation complete!\n\nEvaluated: ${result.total_evaluated} answers\nAverage scores: ${scoreText || 'N/A'}`)

    // Reload results to show evaluation scores
    await loadResults()
  } catch (error) {
    console.error('Evaluation failed:', error)
    alert(`Evaluation failed: ${error.response?.data?.detail || error.message}`)
  } finally {
    evaluating.value = false
  }
}

const evaluateSingleQuestion = async (sectionId, questionId) => {
  const questionKey = `${sectionId}/${questionId}`
  evaluatingQuestion.value = questionKey

  try {
    const result = await api.evaluateQuestion(selectedProject.value, sectionId, questionId)
    console.log(`Evaluation complete for ${questionKey}:`, result)

    // Reload results to show updated evaluation scores
    await loadResults()
  } catch (error) {
    console.error(`Evaluation failed for ${questionKey}:`, error)
    alert(`Evaluation failed: ${error.response?.data?.detail || error.message}`)
  } finally {
    evaluatingQuestion.value = null
  }
}

const openChat = (section, question) => {
  // Set chat context with the question details
  appStore.setChatContext({
    section_id: section.section_id,
    question_id: question.question_id,
    question_text: question.question_name,
    current_answer: question.answer || '',
    current_reference: question.reference || '',
    current_comments: question.comments || ''
  })

  // Navigate to chat/query page
  router.push('/query')
}

// Get CSS class for evaluation score badge
const getScoreClass = (score) => {
  if (score === null || score === undefined) {
    return 'bg-gray-100 text-gray-600'
  }
  if (score >= 4) {
    return 'bg-green-100 text-green-800'
  }
  if (score >= 3) {
    return 'bg-yellow-100 text-yellow-800'
  }
  if (score >= 2) {
    return 'bg-orange-100 text-orange-800'
  }
  return 'bg-red-100 text-red-800'
}
</script>
