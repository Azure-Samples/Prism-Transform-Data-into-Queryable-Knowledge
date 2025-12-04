<template>
  <div class="min-h-screen bg-gray-50 flex flex-col">
    <nav class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex">
            <div class="flex-shrink-0 flex items-center">
              <svg class="h-7 w-7 mr-2" viewBox="0 0 24 24" fill="none">
                <!-- Prism triangle -->
                <path d="M12 2L3 20h18L12 2z" fill="url(#prism-gradient)" stroke="#4F46E5" stroke-width="1.5"/>
                <!-- Light beam entering -->
                <path d="M1 10L8 13" stroke="#9CA3AF" stroke-width="1.5" stroke-linecap="round"/>
                <!-- Refracted spectrum -->
                <path d="M14 14L22 11" stroke="#EF4444" stroke-width="1.5" stroke-linecap="round"/>
                <path d="M15 15L23 14" stroke="#F59E0B" stroke-width="1.5" stroke-linecap="round"/>
                <path d="M15 16L22 17" stroke="#10B981" stroke-width="1.5" stroke-linecap="round"/>
                <path d="M14 17L21 20" stroke="#6366F1" stroke-width="1.5" stroke-linecap="round"/>
                <defs>
                  <linearGradient id="prism-gradient" x1="12" y1="2" x2="12" y2="20" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stop-color="#E0E7FF"/>
                    <stop offset="100%" stop-color="#C7D2FE"/>
                  </linearGradient>
                </defs>
              </svg>
              <h1 class="text-xl font-bold text-gray-900">Prism</h1>
            </div>
            <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
              <router-link
                to="/projects"
                class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                active-class="border-indigo-500 text-gray-900"
              >
                Projects
              </router-link>
              <router-link
                to="/workflows"
                class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                active-class="border-indigo-500 text-gray-900"
              >
                Sections
              </router-link>
              <router-link
                to="/results"
                class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                active-class="border-indigo-500 text-gray-900"
              >
                Results
              </router-link>
              <router-link
                to="/query"
                class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                active-class="border-indigo-500 text-gray-900"
              >
                Query
              </router-link>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <label class="text-sm font-medium text-gray-700">Project:</label>
            <select
              v-model="selectedProject"
              @change="onProjectChange"
              class="block pl-3 pr-10 py-2 text-base text-gray-900 bg-white border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
            >
              <option v-for="project in projects" :key="project.name" :value="project.name">
                {{ project.name.toUpperCase() }}
              </option>
            </select>

            <!-- Help Dropdown -->
            <div class="relative" ref="helpDropdown">
              <button
                @click="showHelpMenu = !showHelpMenu"
                class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md"
                title="Help"
              >
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
              <div
                v-if="showHelpMenu"
                class="absolute right-0 mt-2 w-56 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50"
              >
                <div class="py-1">
                  <div class="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Help & Resources
                  </div>
                  <a
                    href="https://github.com/Azure-Samples/Prism---Transform-Data-into-Queryable-Knowledge#readme"
                    target="_blank"
                    class="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    <svg class="h-4 w-4 mr-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                    Documentation
                  </a>
                  <a
                    href="https://github.com/Azure-Samples/Prism---Transform-Data-into-Queryable-Knowledge/issues/new"
                    target="_blank"
                    class="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    <svg class="h-4 w-4 mr-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    Report an Issue
                  </a>
                  <div class="border-t border-gray-100 my-1"></div>
                  <div class="px-4 py-2 text-xs text-gray-500">
                    <strong>Quick Tips:</strong>
                    <ul class="mt-1 space-y-1">
                      <li>1. Upload documents to a project</li>
                      <li>2. Run the extraction pipeline</li>
                      <li>3. Query your knowledge base</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <!-- GitHub Link -->
            <a
              href="https://github.com/Azure-Samples/Prism---Transform-Data-into-Queryable-Knowledge"
              target="_blank"
              class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md"
              title="View on GitHub"
            >
              <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
            </a>

            <button
              @click="handleLogout"
              class="ml-2 text-sm text-gray-700 hover:text-gray-900"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>

    <main class="flex-1 max-w-7xl mx-auto py-6 sm:px-6 lg:px-8 w-full">
      <router-view :key="selectedProject" />
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-gray-200 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex flex-col sm:flex-row justify-between items-center text-sm text-gray-500">
          <div class="flex items-center space-x-4 mb-2 sm:mb-0">
            <span class="font-medium text-gray-700">Prism</span>
            <span class="text-gray-300">|</span>
            <span>Transform Documents into Queryable Knowledge</span>
          </div>
          <div class="flex items-center space-x-4">
            <a
              href="https://github.com/Azure-Samples/Prism---Transform-Data-into-Queryable-Knowledge"
              target="_blank"
              class="hover:text-gray-700 flex items-center"
            >
              <svg class="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              GitHub
            </a>
            <span class="text-gray-300">|</span>
            <a
              href="https://github.com/Azure-Samples/Prism---Transform-Data-into-Queryable-Knowledge#readme"
              target="_blank"
              class="hover:text-gray-700"
            >
              Docs
            </a>
            <span class="text-gray-300">|</span>
            <a
              href="https://github.com/Azure-Samples/Prism---Transform-Data-into-Queryable-Knowledge/issues/new"
              target="_blank"
              class="hover:text-gray-700"
            >
              Report Issue
            </a>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from './stores/app'
import { storeToRefs } from 'pinia'

const appStore = useAppStore()
const { selectedProject, projects } = storeToRefs(appStore)

const showHelpMenu = ref(false)
const helpDropdown = ref(null)

const handleClickOutside = (event) => {
  if (helpDropdown.value && !helpDropdown.value.contains(event.target)) {
    showHelpMenu.value = false
  }
}

onMounted(async () => {
  await appStore.loadProjects()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

const onProjectChange = () => {
  // Trigger any necessary updates when project changes
  console.log('Project changed to:', selectedProject.value)
}

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  window.location.href = '/login'
}
</script>
