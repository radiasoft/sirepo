// application config:
//   register app-specific field types

import VHeader from '@/apps/cortex/VHeader.vue';
import VSearch from '@/apps/cortex/VSearch.vue';
import { appResources } from '@/services/appresources.js';
import { appState } from '@/services/appstate.js';
import { router } from '@/services/router.js';

appResources.setHeaderComponent(VHeader);

appResources.setAppRoutes([
    {
        name: 'search',
        path: `/search`,
        component: VSearch,
    },
]);
