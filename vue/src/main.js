import "bootstrap"
import "bootstrap-icons/font/bootstrap-icons.css";
import '@/assets/main.css'
import '@/main.scss'
import router from '@/services/router'
import { createApp } from 'vue'
import { appState } from '@/services/appstate.js';
import { authState } from '@/services/authstate.js';

const sirepoLegacyInit = async () => {
    //TODO(pjm): Uses the existing Sirepo API. Create a new API for this
    // that includes the simulationType, schema and authState in one websocket request?

    const addScriptTag = async (url) => {
        const t = document.createElement('script');
        document.body.appendChild(Object.assign(t, {
            src: url,
            type: 'text/javascript',
            async: true,
        }));
        return new Promise((resolve, reject) => t.onload = resolve);
    };

    const checkHTTPResponse = async (response) => {
        if (! response.ok) {
            throw new Error('request failed:', response);
        }
        if (! response.headers.get('content-type').includes('json')) {
            throw new Error(`expected json content-type: ${response.headers.get('content-type')}`);
        }
        return await response.json();
    };

    const fetchWithFormData = async (url, body) => {
        const formData = new URLSearchParams();
        for (const k in body)  {
            formData.append(k, body[k]);
        }
        return await checkHTTPResponse(await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData.toString(),
        }));
    };

    //TODO(pjm): router not yet initialized so use window.location
    // consider sending simulationType with initial SIREPO tag in index.html
    const simulationType = window.location.pathname.split('/')[1];
    if (! simulationType) {
        throw new Error(`missing simulationType in URL path: ${window.location.pathname}`);
    }
    //TODO(pjm): initial schema call must be with form-data?
    const schema = await fetchWithFormData('/simulation-schema', { simulationType });
    appState.init(simulationType, schema);
    globalThis.SIREPO = {};
    await addScriptTag(schema.route.authState);
    authState.init(SIREPO.authState);
    delete globalThis.SIREPO;
};

await sirepoLegacyInit();
import App from '@/App.vue'
createApp(App).use(router).mount('#app')
