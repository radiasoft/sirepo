<template>
    <div v-if="material" class="container-lg">
        <div class="h2">{{ material.name }}</div>
        <div class="row">
            <div class="col-md-6">
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
            <div class="col-md-6">
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
                                v-bind:property="material.composition_density"
                            />
                            <VDOIRows
                                title="Composition"
                                v-bind:property="material.composition"
                            />
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
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
                                    <td class="text-end">{{ r.max_pct ? '' : r.target_pct }}</td>
                                    <td class="text-end">{{ r.min_pct }}</td>
                                    <td class="text-end">{{ r.max_pct }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-12" v-if="material.properties.length">
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
                                        v-bind:property="selectedProperty"
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
        </div>
    </div>
</template>

<script setup>
 import VDOIRows from '@/apps/cortex/VDOIRows.vue';
 import VTooltip from '@/components/VTooltip.vue'
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, ref } from 'vue';
 import { useRoute } from 'vue-router';

 const route = useRoute();
 const material = ref(null);
 const selectedProperty = ref(null);

 const capitalize = (value) => value[0].toUpperCase() + value.slice(1);

 const formatName = (property) => {
     return property.property_name.replaceAll('_', ' ');
 };

 const selectProperty = (property) => {
     selectedProperty.value = property;
 };

 const toYesNo = (value) => {
     if (value === null) {
         return '';
     }
     return value ? 'Yes' : 'No';
 };

 onMounted(async () => {
     const info = await db.materialDetail(route.params.materialId);
     material.value = {
         name: info.material_name,
         density: info.density_g_cm3 + " g/cm³",
         section1: {
             'Material Type': info.is_plasma_facing ? 'plasma-facing' : 'structural',
             Structure: info.structure,
             'Microstructure Information': info.microstructure,
             Processing: info.processing_steps,
         },
         section2: {
             'Neutron Source': info.is_neutron_source_dt ? 'D-T' : 'D-D',
             'Neutron Wall Loading': info.neutron_wall_loading,
             'Availability Factor': info.availability_factor + '%',
         },
         section3: {
             'Bare Tile': toYesNo(info.is_bare_tile),
             'Homogenized WCLL': toYesNo(info.is_homogenized_wcll),
             'Homogenized HCPB': toYesNo(info.is_homogenized_hcpb),
             'Homogenized Divertor': toYesNo(info.is_homogenized_divertor),
         },
         components: info.components,
         composition: info.properties.find((p) => p.property_name === 'composition'),
         composition_density: info.properties.find((p) => p.property_name === 'composition_density'),
         properties: info.properties.filter(p => ! p.property_name.startsWith('composition')),
     };
     for (const c of material.value.components) {
         c.material_component_name = capitalize(c.material_component_name);
         for (const f of ['target_pct', 'min_pct', 'max_pct']) {
             c[f] = c[f] ? c[f].toFixed(4) : c[f];
         }
     }
     for (const p of material.value.properties) {
         p.valueHeadings = {
             value: 'Value' + (p.property_unit ? ` [${p.property_unit}]` : ''),
             uncertainty: 'Uncertainty',
             temperature_k: 'Temperature [K]',
             neutron_fluence_1_cm2: 'Neutron Fluence [1/cm²]',
         };
         if (p.vals && p.vals.length) {
             for (const k in p.vals[0]) {
                 if (k in p.valueHeadings || k.includes('_id')) {
                     continue;
                 }
                 p.valueHeadings[k] = k;
             }
         }
     }
     if (material.value.properties.length) {
         selectedProperty.value = material.value.properties[0];
     }
 });
</script>
