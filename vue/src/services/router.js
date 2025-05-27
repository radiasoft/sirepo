import HomeView from '@/views/HomeView.vue';
import NotFoundView from '@/views/NotFound.vue';
import TestView from '@/views/TestView.vue';
import VRouteMessage from '@/components/VRouteMessage.vue';
import VLogin from '@/components/auth/VLogin.vue';
import VLoginConfirm from '@/components/auth/VLoginConfirm.vue';
import VLoginFail from '@/components/auth/VLoginFail.vue';
import VModerationRequest from '@/components/auth/VModerationRequest.vue';
import VSimulations from '@/components/VSimulations.vue';
import { appState } from '@/services/appstate.js';
import { authState } from '@/services/authstate.js';
import { createRouter, createWebHistory } from 'vue-router';

const storageKey = "previousRoute";

//TODO(pjm): get from local routes in schema
export const routes = {
    completeRegistration: {
        path: '/:simulationType/complete-registration',
        name: 'completeRegistration',
    },
    simulations: {
        path: '/:simulationType/simulations',
        name: 'simulations',
    },
    home: {
        path: '/:simulationType',
        name: 'home',
    },
    about: {
        path: '/:simulationType/about',
        name: 'about',
    },
    test: {
        path: '/:simulationType/test',
        name: 'test',
    },
    login: {
        path: '/:simulationType/login',
        name: 'login',
    },
    loginWithEmailConfirm: {
        path: '/:simulationType/login-with-email-confirm/:token/:needCompleteRegistration',
        name: 'loginWithEmailConfirm',
    },
};

export const router = createRouter({
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
            path: routes.login.path,
            name: routes.login.name,
            component: VLogin,
        },
        {
            path: routes.loginWithEmailConfirm.path,
            name: routes.loginWithEmailConfirm.name,
            component: VLoginConfirm,
        },
        {
            path: routes.simulations.path,
            name: routes.simulations.name,
            component: VSimulations,
        },
        {
            path: routes.completeRegistration.path,
            name: routes.completeRegistration.name,
            component: () => import('@/components/auth/VCompleteRegistration.vue'),
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
            path: '/:simulationType/error',
            name: 'error',
            component: VRouteMessage,
        },
        {
            path: '/:simulationType/login-fail/:method/:reason',
            name: 'loginFail',
            component: VLoginFail,
        },
        {
            path: '/:pathMatch(.*)*',
            component: NotFoundView,
        },
        {
            path: '/:simulationType/subscription-required',
            name: 'planRequired',
            component: VRouteMessage,
        },
        {
            path: '/:simulationType/moderation-request/:role',
            name: 'moderationRequest',
            component: VModerationRequest,
        },
        {
            path: '/:simulationType/moderation-pending',
            name: 'moderationPending',
            component: VRouteMessage,
        },
    ],
})

/* router.beforeEach((to, from, next) => {
 *     console.log('to.name:', to.name);
 *     document.title = routes[to.name].title;
 *     next();
 * });
 * */


    // #checkLoginRedirect(event, route) {
    //     if (! authState.isLoggedIn
    //         || authState.needCompleteRegistration
    //         || route.$$route && route.$$route.sirepoNoLoginRedirect
    //     ) {
    //         return;
    //     }

    //     let p = browserStorage.getString(storageKey);
    //     if (! p) {
    //         return;
    //     }
    //     browserStorage.removeItem(storageKey);
    //     p = p.split(' ');
    //     if (p[0] !== appState.schema.simulationType) {
    //         // wrong app so ignore
    //         return;
    //     }
    //     const r = uri.firstComponent(decodeURIComponent(p[1]));
    //     // After a reload from a login. Only redirect if
    //     // the route is different. The firstComponent is
    //     // always unique in our routes.
    //     if (uri.firstComponent($location.url()) !== r) {
    //         event.preventDefault();
    //         uri.localRedirect(decodeURIComponent(p[1]));
    //     }
    // }

router.beforeEach(async (to, from) => {
    //TODO(pjm): not needed, server will return redirect to login if necessary
    // if (to.name && ! to.name.startsWith('login') && to.params.simulationType && ! authState.isLoggedIn) {
    //     return {
    //         name: 'login',
    //         params: {
    //             simulationType: to.params.simulationType,
    //         },
    //     };
    // }
});
