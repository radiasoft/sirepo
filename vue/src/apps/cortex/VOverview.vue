<template>
    <VMasonry>
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
                    </tbody></table>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card mb-4 shadow-sm">
                <div class="card-body">
                    <div class="h4">
                        Components
                        <h6 class="text-body-secondary" style="display: inline-block">
                            ({{ material.is_atom_pct ? 'Atom' : 'Weight'}} %)
                        </h6>
                    </div>
                    <table class="table">
                        <thead><tr>
                            <th>Element or Nuclide</th>
                            <th class="text-end">Target %</th>
                            <th class="text-end">Min %</th>
                            <th class="text-end">Max %</th>
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
        <div class="col-md-6">
            <div class="card mb-4 shadow-sm">
                <div class="card-body">
                    <table class="table">
                        <tbody><tr>
                            <td style="white-space: nowrap">
                                <div style="display: inline-block" class="lead">
                                    Density
                                </div> <VTooltip
                                    tooltip="Density of your material during in-service conditions; a single value of density will be used for the neutronics calculations"
                                />
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
    </VMasonry>
</template>

<script setup>
 import VDOIRows from '@/apps/cortex/VDOIRows.vue';
 import VMasonry from '@/components/layout/VMasonry.vue'
 import VTooltip from '@/components/VTooltip.vue';

 const props = defineProps({
     material: Object,
 });

 const formatNumber = (value) => {
     return value ? value.toFixed(4) : value;
 };

</script>
