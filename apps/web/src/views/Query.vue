<template>
  <div class="px-4 py-6 sm:px-0">
    <h2 class="text-2xl font-bold text-gray-900 mb-6">Query Documents</h2>

    <!-- Query Form -->
    <div class="bg-white shadow sm:rounded-lg mb-6">
      <div class="px-4 py-5 sm:p-6">
        <form @submit.prevent="handleQuery">
          <div class="space-y-4">
            <div>
              <label for="query" class="block text-sm font-medium text-gray-700">
                Ask a question about your documents
              </label>
              <div class="mt-1">
                <textarea
                  id="query"
                  v-model="query"
                  rows="3"
                  class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                  placeholder="e.g., What can you tell me about our security situation?"
                ></textarea>
              </div>
            </div>
            <div class="flex justify-end">
              <button
                type="submit"
                :disabled="!query.trim() || loading"
                class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                {{ loading ? 'Searching...' : 'Search' }}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- Results -->
    <div v-if="result" class="bg-white shadow sm:rounded-lg">
      <div class="px-4 py-5 sm:p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Answer</h3>

        <!-- Query -->
        <div class="mb-4 p-3 bg-gray-50 rounded-md">
          <p class="text-sm font-medium text-gray-700 mb-1">Question:</p>
          <p class="text-sm text-gray-900">{{ result.query }}</p>
        </div>

        <!-- Answer -->
        <div class="mb-6">
          <p class="text-sm font-medium text-gray-700 mb-2">Answer:</p>
          <div class="prose prose-sm max-w-none text-gray-900 whitespace-pre-wrap">
            {{ result.answer }}
          </div>
        </div>

        <!-- Citations -->
        <div v-if="result.citations && result.citations.length > 0">
          <p class="text-sm font-medium text-gray-700 mb-2">Citations:</p>
          <div class="space-y-2">
            <div
              v-for="(citation, idx) in result.citations"
              :key="idx"
              class="flex items-start p-3 bg-blue-50 rounded-md"
            >
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/>
                </svg>
              </div>
              <div class="ml-3 flex-1">
                <p class="text-sm font-medium text-gray-900">
                  {{ citation.document }}
                </p>
                <p class="text-xs text-gray-500">
                  Page {{ citation.page }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!loading" class="text-center py-12 bg-white shadow rounded-lg">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900">No queries yet</h3>
      <p class="mt-1 text-sm text-gray-500">Get started by asking a question above.</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAppStore } from '../stores/app'
import { storeToRefs } from 'pinia'
import api from '../services/api'

const appStore = useAppStore()
const { selectedProject } = storeToRefs(appStore)

const query = ref('')
const result = ref(null)
const loading = ref(false)

const handleQuery = async () => {
  if (!query.value.trim()) return

  loading.value = true
  result.value = null

  try {
    // Pass project_id so backend can read actual index from project config
    result.value = await api.queryDocuments(query.value, selectedProject.value)
  } catch (error) {
    console.error('Failed to query documents:', error)
    result.value = {
      query: query.value,
      answer: `Error: ${error.message}`,
      citations: []
    }
  } finally {
    loading.value = false
  }
}
</script>
