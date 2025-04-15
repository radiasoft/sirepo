import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import NotFoundView from '@/views/NotFound.vue'

export const routes = {
    HOME: {
        path: '/myapp',
        name: 'Home',
    },
    ABOUT: {
        path: '/myapp/about',
        name: 'About',
    },
};

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            redirect: routes.HOME.path,
        },
        {
            path: routes.HOME.path,
            name: routes.HOME.name,
            component: HomeView,
        },
        {
            path: routes.ABOUT.path,
            name: routes.ABOUT.name,
            // route level code-splitting
            // this generates a separate chunk (About.[hash].js) for this route
            // which is lazy-loaded when the route is visited.
            component: () => import('../views/AboutView.vue'),
        },
        {
            path: '/:pathMatch(.*)*',
            component: NotFoundView,
        },
    ],
})

export default router
