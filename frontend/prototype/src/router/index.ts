import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import SingleTransform from '@/views/SingleTransform.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/singletransform',
      name: 'singletransform',
      component: SingleTransform,
    },
  ],
})

export default router
