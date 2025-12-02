import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Projects from '../views/Projects.vue'
import ProjectDetail from '../views/ProjectDetail.vue'
import WorkflowConfig from '../views/WorkflowConfig.vue'
import Workflows from '../views/Workflows.vue'
import Results from '../views/Results.vue'
import Query from '../views/Query.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/projects'
  },
  {
    path: '/projects',
    name: 'Projects',
    component: Projects,
    meta: { requiresAuth: true }
  },
  {
    path: '/projects/:projectId',
    name: 'ProjectDetail',
    component: ProjectDetail,
    meta: { requiresAuth: true }
  },
  {
    path: '/projects/:projectId/workflow',
    name: 'WorkflowConfig',
    component: WorkflowConfig,
    meta: { requiresAuth: true }
  },
  {
    path: '/workflows',
    name: 'Workflows',
    component: Workflows,
    meta: { requiresAuth: true }
  },
  {
    path: '/results',
    name: 'Results',
    component: Results,
    meta: { requiresAuth: true }
  },
  {
    path: '/query',
    name: 'Query',
    component: Query,
    meta: { requiresAuth: true }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const authToken = localStorage.getItem('auth_token')
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)

  if (requiresAuth && !authToken) {
    // Redirect to login if not authenticated
    next('/login')
  } else if (to.path === '/login' && authToken) {
    // Redirect to home if already authenticated
    next('/projects')
  } else {
    next()
  }
})

export default router
