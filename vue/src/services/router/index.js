import HomeView from '@/views/HomeView.vue'
import NotFoundView from '@/views/NotFound.vue'
import TestView from '@/views/TestView.vue'
import { createRouter, createWebHistory } from 'vue-router'

export const routes = {
    home: {
        path: '/:simulationType',
        name: 'home',
        title: 'Home',
    },
    about: {
        path: '/:simulationType/about',
        name: 'about',
        title: 'About',
    },
    test: {
        path: '/:simulationType/test',
        name: 'test',
        title: 'Test',
    },
};

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            redirect: routes.home.path,
        },
        {
            path: routes.home.path,
            name: routes.home.name,
            component: HomeView,
        },
        {
            path: routes.test.path,
            name: routes.test.name,
            component: TestView,
        },
        {
            path: routes.about.path,
            name: routes.about.name,
            // route level code-splitting
            // this generates a separate chunk (About.[hash].js) for this route
            // which is lazy-loaded when the route is visited.
            component: () => import('@/views/AboutView.vue'),
        },
        {
            path: '/:pathMatch(.*)*',
            component: NotFoundView,
        },
    ],
})

router.beforeEach((to, from, next) => {
    document.title = routes[to.name].title;
    next();
});

export default router
