<template>
    <div v-if="material" class="container-xl">
        <div class="h2">{{ material.name }}</div>
        <VMasonry>
            <div v-bind:class="smallPanel">
                <div class="card mb-4 shadow-sm">
                    <div class="card-body">
                        <table class="table"><tbody>
                            <tr
                                v-for="n in Object.keys(material.section1)"
                                v-bind:key="n"
                            >
                                <td class="col-form-label">{{ n }}</td>
                                <td>{{ material.section1[n] }}</td>
                            </tr>
                            <tr>
                                <td colspan="2" class="lead">
                                    Neutronics Conditions
                                </td>
                            </tr>
                            <tr
                                v-for="n in Object.keys(material.section2)"
                                v-bind:key="n"
                            >
                                <td class="col-form-label">{{ n }}</td>
                                <td>{{ material.section2[n] }}</td>
                            </tr>
                            <tr><td colspan="2" class="lead">Neutronics Geometries</td></tr>
                            <tr
                                v-for="n in Object.keys(material.section3)"
                                v-bind:key="n"
                            >
                                <td class="col-form-label">{{ n }}</td>
                                <td>{{ material.section3[n] }}</td>
                            </tr>
                        </tbody></table>
                    </div>
                </div>
            </div>
            <div v-bind:class="smallPanel">
                <div class="card mb-4 shadow-sm">
                    <div class="card-body">
                        <div class="h4">
                            Components
                            <h6 class="text-body-secondary" style="display: inline-block">
                                ({{ material.is_atom_pct ? 'Atom' : 'Weight'}}%)
                            </h6>
                        </div>
                        <table class="table">
                            <thead><tr>
                                <th>Element or Nuclide</th>
                                <th class="text-end">Target</th>
                                <th class="text-end">Min</th>
                                <th class="text-end">Max</th>
                            </tr></thead>
                            <tbody>
                                <tr
                                    v-for="r in material.components"
                                    v-bind:key="r.material_component_name"
                                >
                                    <td>{{ r.material_component_name }}</td>
                                    <td class="text-end">{{ formatNumber(r.target_pct) }}</td>
                                    <td class="text-end">{{ formatNumber(r.min_pct) }}</td>
                                    <td class="text-end">{{ formatNumber(r.max_pct) }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div v-bind:class="smallPanel">
                <div class="card mb-4 shadow-sm">
                    <div class="card-body">
                        <table class="table">
                            <tbody><tr>
                                <td>
                                    <div style="display: inline-block" class="lead">
                                        Density
                                    </div> <VTooltip
                                        tooltip="Density of your material during in-service conditions; a single value of density will be used for the neutronics calculations" />
                                </td>
                                <td>
                                    <div class="lead">{{ material.density }}</div>
                                </td>
                            </tr></tbody>
                            <VDOIRows
                                v-bind:doi="material.composition_density?.doi"
                            />
                            <VDOIRows
                                title="Composition"
                                v-bind:doi="material.composition?.doi"
                            />
                        </table>
                    </div>
                </div>
            </div>
            <div v-bind:class="largePanel" v-if="material.properties.length">
                <div class="card mb-4 shadow-sm">
                    <div class="card-body">
                        <div class="h4">Properties</div>
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
    </div>
</template>

<script setup>
 import VDOIRows from '@/apps/cortex/VDOIRows.vue';
 import VMasonry from '@/components/layout/VMasonry.vue'
 import VTooltip from '@/components/VTooltip.vue'
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, ref } from 'vue';
 import { useRoute } from 'vue-router';

 const smallPanel = 'col-md-6';
 const largePanel = 'col-md-12';
 const material = ref(null);
 const route = useRoute();
 const selectedProperty = ref(null);

 const formatName = (property) => {
     return property.property_name.replaceAll('_', ' ');
 };

 const formatNumber = (value) => {
     return value ? value.toFixed(4) : value;
 };

 const selectProperty = (property) => {
     selectedProperty.value = property;
 };

 onMounted(async () => {
     material.value = await db.materialDetail(route.params.materialId);
     if (material.value.properties.length) {
         selectedProperty.value = material.value.properties[0];
     }
 });
</script>
