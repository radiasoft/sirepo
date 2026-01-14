<template>
    <div v-if="material" class="container-xl">
        <div class="float-end">
            <VNavButton
                v-bind:active="selectedSection"
                section="overview"
                label="Overview"
                v-on:selected="selectSection"
            ></VNavButton>
            <VNavButton
                v-if="material.properties.length"
                v-bind:active="selectedSection"
                section="properties"
                label="Properties"
                v-on:selected="selectSection"
            ></VNavButton>
            <div class="btn-group">
                <VNavButton
                    v-bind:active="selectedSection"
                    section="neutronics"
                    label="Neutronics"
                    v-on:selected="selectSection"
                ></VNavButton>
                <button
                    class="btn dropdown-toggle dropdown-toggle-split"
                    v-bind:class="{
                        active: isSelected('neutronics'),
                        'btn-primary': isSelected('neutronics'),
                        'btn-light': ! isSelected('neutronics'),
                    }"
                    data-bs-toggle="dropdown"
                ></button>
                <ul class="dropdown-menu" id="sr-neutronics-dropdown-menu">
                    <li><button class="dropdown-item" v-on:click="selectNeutronics('tile')">Homogeneous Tile</button></li>
                </ul>
            </div>
        </div>
        <div class="h2">{{ material.name }}</div>
        <div v-if="isSelected('neutronics')">
            <VNeutronics />
        </div>
        <VMasonry v-if="! isSelected('neutronics')">
            <div v-bind:class="smallPanel">
                <div v-if="isSelected('overview')" class="card mb-4 shadow-sm">
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
                        </tbody></table>
                    </div>
                </div>
            </div>
            <div v-if="isSelected('overview')" v-bind:class="smallPanel">
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
            <div v-if="isSelected('overview')" v-bind:class="smallPanel">
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
            <div v-if="isSelected('properties') && material.properties.length" v-bind:class="largePanel">
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
    </div>
</template>

<script setup>
 import VDOIRows from '@/apps/cortex/VDOIRows.vue';
 import VMasonry from '@/components/layout/VMasonry.vue'
 import VNavButton from '@/apps/cortex/VNavButton.vue';
 import VNeutronics from '@/apps/cortex/VNeutronics.vue';
 import VTooltip from '@/components/VTooltip.vue';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, ref } from 'vue';
 import { useRoute } from 'vue-router';

 const smallPanel = 'col-md-6';
 const largePanel = 'col-md-12';
 const material = ref(null);
 const route = useRoute();
 // overview, properties, neutronics
 const selectedSection = ref('overview');
 const selectedProperty = ref(null);
 // tile
 const selectedNeutronics = ref('tile');

 const formatName = (property) => {
     return property.property_name.replaceAll('_', ' ');
 };

 const formatNumber = (value) => {
     return value ? value.toFixed(4) : value;
 };

 const isSelected = (section) => {
     return selectedSection.value === section;
 };

 const selectNeutronics = (neutronics) => {
     selectedNeutronics.value = neutronics;
     selectSection('neutronics');
 }

 const selectProperty = (property) => {
     selectedProperty.value = property;
 };

 const selectSection = (section) => {
     selectedSection.value = section;
     // bootstrap dropdown doesn't always dismiss correctly when navigating buttons
     const d = document.getElementById('sr-neutronics-dropdown-menu')
     if (d && d.classList) {
         d.classList.remove('show');
     }
 };

 onMounted(async () => {
     material.value = await db.materialDetail(route.params.materialId);
     if (material.value.properties.length) {
         selectedProperty.value = material.value.properties[0];
     }
 });
</script>
