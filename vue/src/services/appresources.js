
import VHeader from '@/components/nav/VHeader.vue';
import VSource from '@/apps/myapp/VSource.vue';
import VVisualization from '@/apps/myapp/VVisualization.vue';
import { schema } from '@/services/schema.js';

import { router } from '@/services/router.js';

class AppResources {
    #appRoutes = [];
    #headerComponent = VHeader;
    #viewLogic = {};
    #widgets = {};

    getAppRoutes() {
        return this.#appRoutes;
    }

    getWidget(name) {
        return this.#widgets[name];
    }

    headerComponent() {
        return this.#headerComponent;
    }

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

    setAppRoutes(routes) {
        for (const r of routes) {
            router.addRoute({
                name: r.name,
                path: `/${schema.simulationType}${r.path}`,
                component: r.component,
            });
        }
        this.#appRoutes = routes.filter(v => v.tabName);
    }

    // allow an app to override the default app header
    setHeaderComponent(component) {
        this.#headerComponent = component;
    }
}

export const appResources = new AppResources();
