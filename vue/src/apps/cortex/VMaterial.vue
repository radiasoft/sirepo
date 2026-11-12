<template>
    <div v-if="error" class="container-lg sr-fixed-lg">
        <div class="alert alert-danger">{{ error }}</div>
        <RouterLink v-bind:to="{ name: 'search' }">Back to Materials</RouterLink>
    </div>
    <VLoadingIndicator v-if="! material && ! error" message="Loading material" />
    <div v-if="material" class="container-lg sr-fixed-lg">
        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
            <div class="h2 mb-0 text-break">{{ material.name }}</div>
            <!-- one group, so a long name wraps it to the next line as a whole, on the right -->
            <div class="d-flex flex-wrap align-items-center justify-content-end gap-2 ms-auto">
                <select
                    v-if="isSelected('neutronics')"
                    class="form-select form-select-sm w-auto"
                    title="Neutronics simulation"
                    v-model="neutronicsSim"
                >
                    <option v-for="r in REPORTS" v-bind:key="r.name" v-bind:value="r.name">
                        {{ r.label }}
                    </option>
                </select>
                <VTabs
                    v-bind:items="sections()"
                    v-bind:pills="true"
                    v-model="selectedSection"
                />
            </div>
        </div>
    </div>
    <div v-if="material">
        <div v-if="isSelected('neutronics')">
            <VNeutronics
                v-bind:materialId="materialId"
                v-bind:materialName="material.name"
                v-bind:isPlasmaFacing="material.is_plasma_facing"
                v-bind:neutronics="neutronicsSim"
            />
        </div>
        <div class="container-lg sr-fixed-lg">
            <div v-if="isSelected('overview')">
                <VOverview
                    v-bind:materialId="materialId"
                    v-bind:material="material"
                />
            </div>
            <div v-if="isSelected('properties')">
                <VProperties v-bind:material="material" />
            </div>
            <div v-if="isSelected('cost')">
                <VCost
                    v-bind:materialId="materialId"
                    v-bind:materialName="material.name"
                    v-bind:isPlasmaFacing="material.is_plasma_facing"
                />
            </div>
        </div>
    </div>
</template>

<script setup>
 import VCost from '@/apps/cortex/VCost.vue';
 import VNeutronics from '@/apps/cortex/VNeutronics.vue';
 import VOverview from '@/apps/cortex/VOverview.vue';
 import VProperties from '@/apps/cortex/VProperties.vue';
 import VLoadingIndicator from '@/components/VLoadingIndicator.vue';
 import VTabs from '@/components/VTabs.vue';
 import { RouterLink } from 'vue-router';
 import { DEFAULT_REPORT, REPORTS } from '@/apps/cortex/reports.js';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, ref } from 'vue';
 import { useRoute } from 'vue-router';
 import { useRouteQuery } from '@/components/useRouteQuery.js';

 const error = ref(null);
 const material = ref(null);
 const materialId = ref(null);
 const route = useRoute();
 // in the url, so refresh, Back and links show the same section and simulation
 const selectedSection = useRouteQuery('section', 'overview', {
     isValid: (v) => sections().some((s) => s.value === v),
     push: true,
 });
 const neutronicsSim = useRouteQuery('sim', DEFAULT_REPORT, {
     isValid: (v) => REPORTS.some((r) => r.name === v),
 });

 const isSelected = (section) => {
     return selectedSection.value === section;
 };

 const sections = () => [
     { value: 'overview', label: 'Overview' },
     // until the material is loaded, properties is assumed, so a link to it works
     ...(! material.value || material.value.properties.length
         ? [{ value: 'properties', label: 'Properties' }]
         : []),
     { value: 'cost', label: 'Cost' },
     { value: 'neutronics', label: 'Neutronics' },
 ];

 onMounted(async () => {
     materialId.value = route.params.materialId;
     try {
         const r = await db.materialDetail(materialId.value, route.name === "view");
         if (r.error) {
             // POSIT: api_cortexDb replies with Not Found for a missing material
             error.value = r.error.value === 'Not Found' ? 'Material not found' : r.error.value;
         }
         else {
             material.value = r.detail;
         }
     }
     catch (e) {
         error.value = 'Unable to load the material, please try again';
     }
 });
</script>
