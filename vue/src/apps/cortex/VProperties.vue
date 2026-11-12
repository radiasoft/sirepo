<template>
    <div v-if="material.properties.length" class="col-md-12">
        <VCortexCard>
            <VTabs
                v-bind:items="material.properties.map((p) => ({ value: p.property_name, label: formatName(p) }))"
                v-model="selectedName"
            />
            <div class="row">
                <div class="col-sm-6">
                    <table class="table">
                        <VDOIRows
                            v-bind:doi="selectedProperty.doi"
                        />
                    </table>
                </div>
            </div>

            <table class="table">
                <thead>
                    <tr>
                        <th
                            class="text-end"
                            v-for="h in Object.keys(selectedProperty.valueHeadings)"
                        >
                            {{ selectedProperty.valueHeadings[h] }}
                        </th>
                    </tr></thead>
                <tbody>
                    <tr
                        v-for="r in selectedProperty.vals"
                    >
                        <td
                            class="text-end"
                            v-for="h in Object.keys(selectedProperty.valueHeadings)"
                        >
                            {{ r[h] }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </VCortexCard>
    </div>
</template>

<script setup>
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VDOIRows from '@/apps/cortex/VDOIRows.vue';
 import VTabs from '@/components/VTabs.vue';
 import { computed } from 'vue';
 import { useRouteQuery } from '@/components/useRouteQuery.js';

 const props = defineProps({
     material: Object,
 });

 const _names = props.material.properties.map((p) => p.property_name);
 // in the url, the first property is the default
 const selectedName = useRouteQuery('property', _names[0] || '', {
     isValid: (v) => _names.includes(v),
 });
 const selectedProperty = computed(
     () => props.material.properties.find((p) => p.property_name === selectedName.value),
 );

 const formatName = (property) => {
     return property.property_name.replaceAll('_', ' ');
 };


</script>
