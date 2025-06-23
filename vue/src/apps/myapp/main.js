// application config:
//   register app-specific field types

// import SpecialType from '@/apps/myapp/SpecialType.vue';
// import { appResources } from '@/services/appresources.js';
// appResources.registerWidget('DogDisposition', SpecialType);

import VSource from '@/apps/myapp/VSource.vue';
import VVisualization from '@/apps/myapp/VVisualization.vue';
import { appResources } from '@/services/appresources.js';
import { appState } from '@/services/appstate.js';
import { watch } from 'vue';

appResources.setAppRoutes([
    {
        name: 'source',
        path: `/source/:simulationId`,
        component: VSource,
        tabName: 'Source',
        tabIconClass: 'bi-lightning',
    },
    {
        name: 'visualization',
        path: `/visualization/:simulationId`,
        component: VVisualization,
        tabName: 'Visualization',
        tabIconClass: 'bi-card-image',
        tabVisible: () => appState.models.dog.weight > 100,
    },
]);

appResources.registerViewLogic('dog', (ui_ctx) => {
    watch(ui_ctx, () => {
        if ('favoriteTreat' in ui_ctx.fields) {
            ui_ctx.fields.favoriteTreat.visible = ui_ctx.fields.disposition.val === 'friendly';
        }
    });
});
