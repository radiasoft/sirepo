
import { appState } from '@/services/appstate.js';
import { router } from '@/services/router.js';

class URI {
    formatLocal(routeName, params) {
        //TODO(pjm): improve to use params
        return `/${appState.simulationType}${appState.schema.localRoutes[routeName].route}`;
    }

    globalRedirect(uri) {
        router.push(uri);
    }

    localRedirect(routeName, params) {
        router.push({
            name: routeName,
            params: {
                ...(params || {}),
                simulationType: appState.simulationType,
            },
        });
    }

    redirectAppRoot() {
        //TODO(pjm): use formatter
        router.push('/' + appState.simulationType);
    }
}

export const uri = new URI();
