// application config:
//   register app-specific field types

import VHeader from '@/apps/cortex/VHeader.vue';
import VMaterial from '@/apps/cortex/VMaterial.vue';
import VSearch from '@/apps/cortex/VSearch.vue';
import { appResources } from '@/services/appresources.js';
import { appState } from '@/services/appstate.js';
import { router } from '@/services/router.js';

appResources.setHeaderComponent(VHeader);

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
