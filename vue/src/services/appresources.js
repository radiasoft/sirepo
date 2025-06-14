
import VHeader from '@/components/header/VHeader.vue';
import VSource from '@/apps/myapp/VSource.vue';
import VVisualization from '@/apps/myapp/VVisualization.vue';
import { appState } from '@/services/appstate.js';

import { router } from '@/services/router.js';

class AppResources {
    #headerComponent = VHeader;
    #localRoutes = [];
    #viewLogic = {};
    #widgets = {};

    initViewLogic(viewName, ui_ctx) {
        const v = this.#viewLogic[viewName];
        if (v) {
            v(ui_ctx);
        }
    }

    registerViewLogic(viewName, useFunction) {
        this.#viewLogic[viewName] = useFunction;
    }

    registerWidget(name, component) {
        this.#widgets[name] = component;
    }

    getWidget(name) {
        return this.#widgets[name];
    }

    headerComponent() {
        return this.#headerComponent;
    }

    // allow an app to override the default app header
    setHeaderComponent(component) {
        this.#headerComponent = component;
    }

    getLocalRoutes() {
        return this.#localRoutes;
    }

    setLocalRoutes(routes) {
        this.#localRoutes = routes;
        for (const r of routes) {
            router.addRoute({
                name: r.name,
                path: r.path,
                component: r.component,
            });
        }
    }
}

export const appResources = new AppResources();
