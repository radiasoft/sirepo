// application config:
//   register app-specific field types

import VBatch from '@/apps/cortex/VBatch.vue';
import VHeader from '@/apps/cortex/VHeader.vue';
import VSearch from '@/apps/cortex/VSearch.vue';
import VMaterial from '@/apps/cortex/VMaterial.vue';
import { appResources } from '@/services/appresources.js';
import { authState } from '@/services/authstate.js';
import { schema } from '@/services/schema.js';

appResources.setHeaderComponent(VHeader);

appResources.setAppRoutes([
    {
        name: 'search',
        path: `/search`,
        component: VSearch,
    },
    {
        name: 'batch',
        path: `/batch`,
        component: VBatch,
        // authState is initialized before the router is (see src/main.js)
        beforeEnter: () => authState.isAdm() || { name: 'search' },
    },
    {
        name: 'material',
        path: `/material/:materialId`,
        component: VMaterial,
    },
    {
        name: 'view',
        path: `/view/:materialId`,
        component: VMaterial,
    },
]);

// no simulations page for this app
delete schema.localRoutes['simulations'];
