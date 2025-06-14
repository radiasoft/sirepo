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

appResources.setLocalRoutes([
    {
        name: 'source',
        path: `/${appState.simulationType}/source/:simulationId`,
        component: VSource,
        displayName: 'Source',
        iconClass: 'bi-lightning',
    },
    {
        name: 'visualization',
        path: `/${appState.simulationType}/visualization/:simulationId`,
        component: VVisualization,
        displayName: 'Visualization',
        iconClass: 'bi-card-image',
        visible: () => appState.models.dog.weight > 100,
    },
]);

appResources.registerViewLogic('dog', (ui_ctx) => {
    watch(ui_ctx, () => {
        if ('favoriteTreat' in ui_ctx.fields) {
            ui_ctx.fields.favoriteTreat.visible = ui_ctx.fields.disposition.val === 'friendly';
        }
    });
});
