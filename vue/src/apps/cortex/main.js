

// application config:
//   register app-specific field types

import { appState } from '@/services/appstate.js';
import { router } from '@/services/router.js';

import VMaterial from '@/apps/cortex/VMaterial.vue';
import VSearch from '@/apps/cortex/VSearch.vue';

router.addRoute({
    name: 'material',
    path: `/${appState.simulationType}/material/:simulationId`,
    component: VMaterial,
});
router.addRoute({
    name: 'search',
    path: `/${appState.simulationType}/search`,
    component: VSearch,
});
