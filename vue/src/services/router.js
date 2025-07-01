import VLogin from '@/components/auth/VLogin.vue';
import VLoginConfirm from '@/components/auth/VLoginConfirm.vue';
import VLoginFail from '@/components/auth/VLoginFail.vue';
import VModerationRequest from '@/components/auth/VModerationRequest.vue';
import VRouteMessage from '@/components/VRouteMessage.vue';
import VSimOrganizer from '@/components/VSimOrganizer.vue';
import { appState } from '@/services/appstate.js';
import { authState } from '@/services/authstate.js';
import { createRouter, createWebHistory } from 'vue-router';
import { schema } from '@/services/schema.js';

const storageKey = "previousRoute";

const routeComponents = {
    completeRegistration: () => import('@/components/auth/VCompleteRegistration.vue'),
    error: VRouteMessage,
    login: VLogin,
    loginFail: VLoginFail,
    loginWithEmailConfirm: VLoginConfirm,
    moderationPending: VRouteMessage,
    moderationRequest: VModerationRequest,
    notFound: VRouteMessage,
    planRequired: VRouteMessage,
    simulations: VSimOrganizer,
};

export const initRouter = () => {
    const t = schema.simulationType;
    router.addRoute({
        path: `/${t}`,
        redirect: `/${t}/${schema.appDefaults.route}`,
    });
    for (const [n, r] of Object.entries(schema.localRoutes)) {
        if (routeComponents[n]) {
            router.addRoute({
                name: n,
                path: `/${t}${r.route}`,
                component: routeComponents[n],
            });
        }
    }
    router.addRoute({
        name: 'noRoute',
        path: '/:pathMatch(.*)*',
        component: VRouteMessage,
    });
    return router
};

export const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        //TODO(pjm): need default not-found handler
    ],
});

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
    //     if (p[0] !== schema.simulationType) {
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
    //TODO(pjm): document.title should update on modelChanged as well
    const t = schema.appInfo[schema.simulationType].shortName + ' - '
            + schema.productInfo.shortName
    document.title = t;
    if (to.params.simulationId) {
        if (appState.isLoadedRef.value) {
            if (appState.models.simulation.simulationId !== to.params.simulationId) {
                throw new Error('simulationId is loaded, but navigated to a different simulationId');
            }
            return;
        }
        await appState.loadModels(to.params.simulationId);
        document.title = `${appState.models.simulation.name} - ${t}`;
    }
});
