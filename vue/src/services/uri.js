
import { appState } from '@/services/appstate.js';
import { router } from '@/services/router.js';

class URI {
    format(routeName, params) {
        params = params || {};
        params.simulation_type = appState.simulationType;
        const u = appState.schema.route[routeName];
        let r = u;
        for (const m of u.matchAll(/([\?\*]?)<(\w+)>/g)) {
            const [token, optional, name] = m;
            if (name in params) {
                r = r.replaceAll(token, params[name]);
            }
            else if (! optional) {
                throw new Error(`Mising uri param: ${name}`);
            }
            else {
                r = r.replaceAll(token, '');
            }
        }
        return r;
    }

    globalRedirect(uri) {
        router.push(uri);
    }

    localRedirect(routeName, params) {
        router.push({
            name: routeName,
            params: params || {},
        });
    }

    localRedirectHome(simulationId) {
        uri.localRedirect(
            appState.schema.appModes.default.localRoute,
            { simulationId },
        );
    }

    redirectAppRoot() {
        //TODO(pjm): use formatter
        router.push('/' + appState.simulationType);
    }
}

export const uri = new URI();
