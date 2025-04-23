import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import NotFoundView from '@/views/NotFound.vue'

export const routes = {
    home: {
        path: '/myapp',
        name: 'home',
        title: 'Home',
    },
    about: {
        path: '/myapp/about',
        name: 'about',
        title: 'About',
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
