<template>
    <div class="container-xl sr-fixed-lg">
        <VLoadingIndicator v-bind:message="loadingMessage" />
        <div v-if="materialCount === 0">
            <p class="lead text-center">Welcome to the Material Database</p>
        </div>
        <div class="row">
            <div class="col-sm-8">
                <div v-if="featuredMaterials">
                    <VFeaturedMaterials v-bind:rows="featuredMaterials" />
                </div>
            </div>
            <div
                v-show="materialCount !== undefined"
                v-bind:class="{
                    'col-sm-4': featuredMaterials,
                    'col-sm-6 offset-sm-3': ! featuredMaterials,
                }"
            >
                <VImportXLSXPanel />
            </div>
        </div>
        <div class="p-3" v-if="! featuredMaterials"></div>
        <div class="row">
            <div v-show="materialCount" class="col-sm-12">
                <VCortexCard title="Your Materials" v-show="materialCount">
                    <template v-slot:header>
                        <div class="d-flex gap-2">
                            <select
                                class="form-select form-select-sm w-auto"
                                title="Simulation of the results shown"
                                v-model="report"
                            >
                                <option
                                    v-for="r in REPORTS"
                                    v-bind:key="r.name"
                                    v-bind:value="r.name"
                                >
                                    {{ r.label }}
                                </option>
                            </select>
                            <input
                                type="text"
                                class="form-control form-control-sm"
                                placeholder="Filter by name or type"
                                v-model="filter"
                            />
                            <VPager
                                v-model:page="page"
                                v-bind:compact="true"
                                v-bind:pageCount="pageCount"
                            />
                        </div>
                    </template>
                    <VMaterialTable
                        v-model:page="page"
                        v-model:pageCount="pageCount"
                        v-bind:filter="filter"
                        v-bind:report="report"
                        v-on:materialCount="updateMaterialCount"
                    />
                </VCortexCard>
            </div>
        </div>
    </div>
</template>

<script setup>
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VFeaturedMaterials from '@/apps/cortex/VFeaturedMaterials.vue';
 import VImportXLSXPanel from '@/apps/cortex/VImportXLSXPanel.vue';
 import VLoadingIndicator from '@/components/VLoadingIndicator.vue';
 import VMaterialTable from '@/apps/cortex/VMaterialTable.vue';
 import VPager from '@/apps/cortex/VPager.vue';
 import { DEFAULT_REPORT, REPORTS } from '@/apps/cortex/reports.js';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted } from 'vue';
 import { ref } from 'vue';
 import { useRouteQuery } from '@/components/useRouteQuery.js';

 // in the url, so refresh, Back and links show the same list. The page isn't,
 // because it depends on the sort, which isn't either.
 const filter = useRouteQuery('q', '');
 const report = useRouteQuery('sim', DEFAULT_REPORT, {
     isValid: (v) => REPORTS.some((r) => r.name === v),
 });
 const materialCount = ref(0);
 const page = ref(1);
 const pageCount = ref(1);
 const loadingMessage = ref('');
 const featuredMaterials = ref(null);

 const updateMaterialCount = (size) => {
     loadingMessage.value = size === undefined ? 'Connecting to the database' : '';
     materialCount.value = size;
 };

 onMounted(async () => {
     featuredMaterials.value = (await db.featuredMaterials()).rows;
     if (featuredMaterials.value && ! featuredMaterials.value.length) {
         featuredMaterials.value = null;
     }
 });

</script>
