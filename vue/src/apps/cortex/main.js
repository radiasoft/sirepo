// application config:
//   register app-specific field types

import VHeader from '@/apps/cortex/VHeader.vue';
import VSearch from '@/apps/cortex/VSearch.vue';
import VMaterial from '@/apps/cortex/VMaterial.vue';
import { appResources } from '@/services/appresources.js';
import { schema } from '@/services/schema.js';

appResources.setHeaderComponent(VHeader);

appResources.setAppRoutes([
    {
        name: 'search',
        path: `/search`,
        component: VSearch,
    },
    {
        name: 'material',
        path: `/material/:materialId`,
        component: VMaterial,
    },
]);

// no simulations page for this app
delete schema.localRoutes['simulations'];
