<template>
    <VMasonry>
        <div class="col-md-6">
            <VCortexCard>
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
            </VCortexCard>
        </div>
        <div class="col-md-6" v-if="showPublic">
            <VCortexCard v-if="! material.is_public">
                <span style="line-height: 40px; vertical-align: bottom">This material is private.</span>
                <button
                    type="button"
                    class="btn btn-outline-primary float-end"
                    v-on:click="setPublic(true)"
                >
                    Allow Public Access
                    <VTooltip tooltip="Publicly accessible materials can be viewed by any user" />
                </button>
            </VCortexCard>
            <VCortexCard v-if="material.is_public">
                <span style="line-height: 40px; vertical-align: bottom">This material is public.</span>
                <button
                    type="button"
                    class="btn btn-outline-primary float-end"
                    v-on:click="setPublic(false)"
                >
                    Remove Public Access
                    <VTooltip tooltip="Remove this material from public access" />
                </button>
            </VCortexCard>
        </div>
        <div class="col-md-6">
            <VCortexCard>
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
            </VCortexCard>
        </div>
        <div class="col-md-6">
            <VCortexCard>
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
                            <div class="lead">{{ material.density }} {{ material.density_units }}</div>
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
            </VCortexCard>
        </div>
    </VMasonry>
    <VConfirmationModal
        ref="confirm"
        cancelText="Close"
        title="Error"
    >
        Both neutronics simulations (Homogeneous Tile and Slab) need to be completed before
        a material can be made publicly available.
    </VConfirmationModal>
</template>

<script setup>
 import VConfirmationModal from '@/components/VConfirmationModal.vue';
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VDOIRows from '@/apps/cortex/VDOIRows.vue';
 import VMasonry from '@/components/layout/VMasonry.vue'
 import VTooltip from '@/components/VTooltip.vue';
 import { db } from '@/apps/cortex/db.js';
 import { ref } from 'vue';
 import { useRoute } from 'vue-router';

 const props = defineProps({
     material: Object,
     materialId: String,
 });

 const confirm = ref(null);
 const route = useRoute();
 const showPublic = ref(route.name === "material");

 const formatNumber = (value) => {
     return value ? value.toFixed(4) : value;
 };

 const setPublic = async (isPublic) => {
     if (isPublic) {
         if (! (await db.canSetMaterialPublic(props.materialId))) {
             confirm.value.showModal();
             return;
         }
     }
     const r = await db.setMaterialPublic(props.materialId, isPublic);
     if (! r.error) {
         props.material.is_public = isPublic;
     }
 };

</script>
