<template>
  <div class="px-4 py-6 sm:px-0 flex flex-col h-[calc(100vh-100px)]">
    <!-- Header with context info -->
    <div class="mb-3 flex-shrink-0">
      <div class="flex justify-between items-start">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">
            {{ chatContext ? 'Discuss Result' : 'Search Documents' }}
          </h2>
          <p class="text-sm text-gray-500 mt-1">
            {{ chatContext ? 'Ask follow-up questions about this result' : 'Ask questions about your indexed documents' }}
          </p>
        </div>
        <button
          v-if="chatContext"
          @click="clearContext"
          class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
          Clear Context
        </button>
      </div>
    </div>

    <!-- Context Card (when discussing a specific question) - minimal -->
    <div v-if="chatContext" class="mb-2 bg-indigo-50 border border-indigo-200 rounded-lg px-3 py-2 flex-shrink-0">
      <div class="flex items-center gap-2 text-xs">
        <span class="font-medium text-indigo-600">{{ chatContext.section_id }}/{{ chatContext.question_id }}:</span>
        <span class="text-gray-900 truncate flex-1">{{ truncate(chatContext.question_text, 80) }}</span>
        <span class="text-gray-500">Answer: {{ truncate(chatContext.current_answer, 30) || 'N/A' }}</span>
      </div>
    </div>

    <!-- Chat Messages - takes all remaining space -->
    <div class="flex-1 bg-white shadow rounded-lg overflow-hidden flex flex-col min-h-0">
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        <!-- Empty state -->
        <div v-if="chatHistory.length === 0" class="text-center py-12">
          <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900">
            {{ chatContext ? 'Ask about this result' : 'Start a conversation' }}
          </h3>
          <p class="mt-1 text-sm text-gray-500">
            {{ chatContext ? 'Ask follow-up questions to get more details or clarification' : 'Type a question to search your documents' }}
          </p>
        </div>

        <!-- Messages -->
        <div
          v-for="(message, idx) in chatHistory"
          :key="idx"
          :class="[
            'flex w-full',
            message.role === 'user' ? 'justify-end' : 'justify-start'
          ]"
        >
          <div
            :class="[
              'max-w-[85%] rounded-lg px-4 py-3 shadow-sm border',
              message.role === 'user'
                ? 'bg-indigo-600 text-white border-indigo-700'
                : 'bg-slate-50 text-gray-900 border-slate-200'
            ]"
          >
            <p class="text-sm whitespace-pre-wrap leading-relaxed">{{ message.content }}</p>
          </div>
        </div>

        <!-- Loading indicator -->
        <div v-if="loading" class="flex justify-start">
          <div class="bg-gray-100 rounded-lg px-4 py-2">
            <div class="flex items-center gap-2">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
              <span class="text-sm text-gray-500">Searching documents...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input area -->
      <div class="border-t border-gray-200 p-4">
        <form @submit.prevent="sendMessage" class="flex gap-2">
          <input
            v-model="inputMessage"
            type="text"
            :placeholder="chatContext ? 'Ask a follow-up question...' : 'Ask a question about your documents...'"
            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white text-gray-900"
            :disabled="loading"
          />
          <button
            type="submit"
            :disabled="!inputMessage.trim() || loading"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </form>
      </div>
    </div>

    <!-- Update Result Panel (only when context is set) - collapsible -->
    <div v-if="chatContext && chatHistory.length > 0" class="mt-2 bg-white shadow rounded-lg flex-shrink-0">
      <button
        @click="showUpdatePanel = !showUpdatePanel"
        class="w-full px-3 py-2 flex items-center justify-between text-sm font-medium text-gray-900 hover:bg-gray-50 rounded-lg"
      >
        <span>Update Original Result</span>
        <svg
          :class="['w-4 h-4 transition-transform', showUpdatePanel ? 'rotate-180' : '']"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div v-show="showUpdatePanel" class="px-3 pb-3">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">New Answer</label>
            <input
              v-model="updateForm.answer"
              type="text"
              class="w-full px-2 py-1 border border-gray-300 rounded text-sm bg-white text-gray-900"
              placeholder="Updated answer..."
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">New Reference</label>
            <input
              v-model="updateForm.reference"
              type="text"
              class="w-full px-2 py-1 border border-gray-300 rounded text-sm bg-white text-gray-900"
              placeholder="Document references..."
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">New Comments</label>
            <input
              v-model="updateForm.comments"
              type="text"
              class="w-full px-2 py-1 border border-gray-300 rounded text-sm bg-white text-gray-900"
              placeholder="Additional comments..."
            />
          </div>
        </div>
        <div class="mt-2 flex justify-end gap-2">
          <button
            @click="copyLastResponse"
            class="px-2 py-1 text-xs border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
          >
            Copy Last Response
          </button>
          <button
            @click="updateResult"
            :disabled="updating || (!updateForm.answer && !updateForm.reference && !updateForm.comments)"
            class="px-2 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ updating ? 'Updating...' : 'Update Result' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useAppStore } from '../stores/app'
import { storeToRefs } from 'pinia'
import api from '../services/api'

const appStore = useAppStore()
const { selectedProject, chatContext, chatHistory } = storeToRefs(appStore)

const inputMessage = ref('')
const loading = ref(false)
const updating = ref(false)
const messagesContainer = ref(null)
const showUpdatePanel = ref(false)

const updateForm = ref({
  answer: '',
  reference: '',
  comments: ''
})

// Helper to truncate long text
const truncate = (text, maxLength) => {
  if (!text) return text
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

// Watch for context changes and pre-fill update form
watch(chatContext, (newContext) => {
  if (newContext) {
    updateForm.value = {
      answer: newContext.current_answer || '',
      reference: newContext.current_reference || '',
      comments: newContext.current_comments || ''
    }
  } else {
    updateForm.value = { answer: '', reference: '', comments: '' }
  }
}, { immediate: true })

// Scroll to bottom when new messages arrive
watch(chatHistory, async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}, { deep: true })

const clearContext = () => {
  appStore.clearChatContext()
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  // Add user message to history
  appStore.addChatMessage('user', message)

  loading.value = true

  try {
    const response = await api.sendChatMessage(
      selectedProject.value,
      message,
      chatContext.value,
      chatHistory.value.slice(0, -1) // Don't include the message we just added
    )

    // Add assistant response to history
    appStore.addChatMessage('assistant', response.message)

  } catch (error) {
    console.error('Chat error:', error)
    appStore.addChatMessage('assistant', `Error: ${error.message || 'Failed to get response'}`)
  } finally {
    loading.value = false
  }
}

const copyLastResponse = () => {
  // Find last assistant message
  const lastAssistant = [...chatHistory.value].reverse().find(m => m.role === 'assistant')
  if (lastAssistant) {
    const content = lastAssistant.content

    // Split content at "=== SOURCE DOCUMENTS ===" to separate answer from citations
    const parts = content.split('=== SOURCE DOCUMENTS ===')
    const mainContent = parts[0].trim()
    const sourceDocs = parts[1] || ''

    // Extract the main answer (everything before source docs)
    // Limit to reasonable length
    const answerText = mainContent.substring(0, 1000)

    // Try to extract document references from SOURCE DOCUMENTS section
    const docMatches = sourceDocs.match(/\d+\.\s+(.+?)(?=\n|$)/g)
    const references = docMatches
      ? docMatches.slice(0, 3).map(m => m.replace(/^\d+\.\s+/, '').trim()).join('; ')
      : ''

    // Set form values
    updateForm.value.answer = answerText
    updateForm.value.reference = references
    updateForm.value.comments = ''
  }
}

const updateResult = async () => {
  if (!chatContext.value) return

  updating.value = true

  try {
    await api.updateResultFromChat(
      selectedProject.value,
      chatContext.value.section_id,
      chatContext.value.question_id,
      updateForm.value
    )

    // Update the context with new values
    if (updateForm.value.answer) chatContext.value.current_answer = updateForm.value.answer
    if (updateForm.value.reference) chatContext.value.current_reference = updateForm.value.reference
    if (updateForm.value.comments) chatContext.value.current_comments = updateForm.value.comments

    alert('Result updated successfully!')

  } catch (error) {
    console.error('Update error:', error)
    alert(`Failed to update result: ${error.message}`)
  } finally {
    updating.value = false
  }
}
</script>
