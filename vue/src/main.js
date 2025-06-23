import "bootstrap";
import "bootstrap-icons/font/bootstrap-icons.css";
import '@/main.scss';
import App from '@/App.vue';
import { appState } from '@/services/appstate.js';
import { authState } from '@/services/authstate.js';
import { createApp } from 'vue';
import { onError } from '@/services/errorhandler.js';
import { initRouter } from '@/services/router.js';

// this must come last to override bootstrap css values
import '@/assets/main.css';

const sirepoLegacyInit = () => {
    //TODO(pjm): Uses the existing Sirepo API. Create a new API for this
    // that includes the simulationType, schema and authState in one websocket request?

    const addScriptTag = (url) => {
        const t = document.createElement('script');
        document.body.appendChild(Object.assign(t, {
            src: url,
            type: 'text/javascript',
            async: true,
        }));
        return new Promise((resolve, reject) => t.onload = resolve);
    };

    const checkHTTPResponse = (response) => {
        if (! response.ok) {
            throw new Error('request failed:', response);
        }
        if (! response.headers.get('content-type').includes('json')) {
            throw new Error(`expected json content-type: ${response.headers.get('content-type')}`);
        }
        return response.json();
    };

    const fetchWithFormData = (url, body) => {
        const formData = new URLSearchParams();
        for (const k in body)  {
            formData.append(k, body[k]);
        }
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData.toString(),
        }).then(checkHTTPResponse);
    };

    //TODO(pjm): router not yet initialized so use window.location
    // consider sending simulationType with initial SIREPO tag in index.html
    const simulationType = window.location.pathname.split('/')[1];
    if (! simulationType) {
        throw new Error(`missing simulationType in URL path: ${window.location.pathname}`);
    }
    //TODO(pjm): initial schema call must be with form-data?
    return fetchWithFormData('/simulation-schema', { simulationType }).then(
        (schema) => {
            appState.init(simulationType, schema);
            globalThis.SIREPO = {};
            return addScriptTag(schema.route.authState);
        }).then(() => {
            authState.init(SIREPO.authState);
            delete globalThis.SIREPO;
            return simulationType;
        });
};

sirepoLegacyInit().then((simulationType) => {
    const app = createApp(App);
    app.config.errorHandler = onError;
    import(`@/apps/${simulationType}/main.js`).then(() => {
        const r = initRouter();
        r.onError(onError);
        app.use(r).mount('#app');
    });
}).catch((message) => {
    throw new Error(message);
});
