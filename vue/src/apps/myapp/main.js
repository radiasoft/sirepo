

// application config:
//   register app-specific field types

// import SpecialType from '@/apps/myapp/SpecialType.vue';
// import { appState } from '@/services/appstate.js';
// appState.registerWidget('DogDisposition', SpecialType);


import { appState } from '@/services/appstate.js';
import { router } from '@/services/router.js';
import { watch } from 'vue';

import VSource from '@/apps/myapp/VSource.vue';

router.addRoute({
    name: 'source',
    path: `/${appState.simulationType}/source/:simulationId`,
    component: VSource,
});

appState.registerViewLogic('dog', (ui_ctx) => {
    watch(ui_ctx, () => {
        if ('favoriteTreat' in ui_ctx.fields) {
            ui_ctx.fields.favoriteTreat.visible = ui_ctx.fields.disposition.val === 'friendly';
        }
    });
});
