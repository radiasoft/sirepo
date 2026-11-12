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
            <VCortexCard title="Public Access">
                <p>
                    This material is <strong>{{ material.is_public ? 'public' : 'private' }}</strong>.
                    <span class="text-muted">Public materials can be viewed by any user.</span>
                </p>
                <button
                    type="button"
                    class="btn btn-outline-primary"
                    v-bind:disabled="isSaving || ! canToggle()"
                    v-on:click="setPublic(! material.is_public)"
                >
                    <span v-if="isSaving" class="spinner-border spinner-border-sm"></span>
                    {{ material.is_public ? 'Remove Public Access' : 'Allow Public Access' }}
                </button>
                <div v-if="! canToggle()" class="form-text">
                    Run the HCPB Slab neutronics simulation before making
                    this material public.
                </div>
                <div v-if="error" class="text-danger mt-2">{{ error }}</div>
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
</template>

<script setup>
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VDOIRows from '@/apps/cortex/VDOIRows.vue';
 import VMasonry from '@/components/layout/VMasonry.vue'
 import VTooltip from '@/components/VTooltip.vue';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, ref } from 'vue';
 import { useRoute } from 'vue-router';

 const props = defineProps({
     material: Object,
     materialId: String,
 });

 const MIN_SAVING_MS = 500;
 const error = ref('');
 const isSaving = ref(false);
 const route = useRoute();
 const showPublic = ref(route.name === "material");

 const formatNumber = (value) => {
     return value ? value.toFixed(4) : value;
 };

 // POSIT: material_db _PUBLIC_MODEL results are needed to make it public
 const canToggle = () => props.material.is_public || props.material.can_be_public;

 const setPublic = async (isPublic) => {
     error.value = '';
     isSaving.value = true;
     try {
         // a fast reply would flash the spinner, so it shows for at least this long
         const [r] = await Promise.all([
             db.setMaterialPublic(props.materialId, isPublic),
             new Promise((resolve) => setTimeout(resolve, MIN_SAVING_MS)),
         ]);
         if (r.error) {
             error.value = r.error.value;
             return;
         }
         props.material.is_public = isPublic;
     }
     catch (e) {
         error.value = 'Unable to change public access, please try again';
     }
     finally {
         isSaving.value = false;
     }
 };

 onMounted(async () => {
     // the simulation may have completed since the material was loaded
     if (showPublic.value && ! canToggle()) {
         const r = await db.materialDetail(props.materialId, false);
         if (r.detail) {
             props.material.can_be_public = r.detail.can_be_public;
         }
     }
 });

</script>
