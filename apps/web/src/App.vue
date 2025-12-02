<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex">
            <div class="flex-shrink-0 flex items-center">
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
            <button
              @click="handleLogout"
              class="ml-4 text-sm text-gray-700 hover:text-gray-900"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from './stores/app'
import { storeToRefs } from 'pinia'

const appStore = useAppStore()
const { selectedProject, projects } = storeToRefs(appStore)

onMounted(async () => {
  await appStore.loadProjects()
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
