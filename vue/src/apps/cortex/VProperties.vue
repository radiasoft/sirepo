<template>
    <VMasonry>
        <div v-if="material.properties.length" class="col-md-12">
            <div class="card mb-4 shadow-sm">
                <div class="card-body">
                    <div class="nav nav-tabs">
                        <li
                            class="nav-item"
                            v-for="p in material.properties"
                            v-bind:key="p"
                        >
                            <button
                                type="button"
                                class="nav-link"
                                v-bind:class="{
                                    active: p == selectedProperty,
                                }"
                                v-on:click="selectProperty(p)"
                            >
                                {{ formatName(p) }}
                            </button>
                        </li>
                    </div>
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
                </div>
            </div>
        </div>
    </VMasonry>
</template>

<script setup>
 import VDOIRows from '@/apps/cortex/VDOIRows.vue';
 import VMasonry from '@/components/layout/VMasonry.vue'
 import { ref } from 'vue';

 const props = defineProps({
     material: Object,
 });

 const selectedProperty = ref(null);

 const formatName = (property) => {
     return property.property_name.replaceAll('_', ' ');
 };

 const selectProperty = (property) => {
     selectedProperty.value = property;
 };

 if (props.material.properties.length) {
     selectedProperty.value = props.material.properties[0];
 }

</script>
