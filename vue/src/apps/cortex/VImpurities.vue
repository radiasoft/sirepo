<template>
    <!-- one root element: VNeutronics.vue shows the tab with v-show -->
    <div>
        <div class="row">
            <div class="col-lg-4">
                <VCortexCard
                    v-for="r in RUNS"
                    v-bind:key="r.impurity"
                    v-bind:title="r.title"
                >
                    <div v-if="runs[r.impurity]">
                        <b>Completed:</b> {{ util.formatDate(runs[r.impurity].completed) }}
                        <div
                            v-if="runs[r.impurity].version !== runs[r.impurity].current_version"
                            class="text-warning"
                        >
                            This simulation was run with an older model.
                        </div>
                    </div>
                    <VRunSim
                        v-if="! isViewing && isLoaded"
                        v-bind:sim="sims[r.impurity]"
                        v-bind:viewName="impurityReport(neutronics, r.impurity)"
                    />
                </VCortexCard>
            </div>
            <div class="col-lg-4">
                <VCortexCard title="Impurities">
                    <div class="text-muted small mb-2">
                        Components with a minimum of 0. The comparison runs the
                        simulation with them at their maximum and with none of
                        them; {{ balance }} takes up the difference.
                    </div>
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Element or Nuclide</th>
                                <th class="text-end">Max %</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="c in impurities" v-bind:key="c.material_component_name">
                                <td>{{ c.material_component_name }}</td>
                                <td class="text-end">{{ c.max_pct }}</td>
                            </tr>
                        </tbody>
                    </table>
                </VCortexCard>
            </div>
            <div class="col-lg-4">
                <VCortexCard v-bind:title="layer ? `Impurity Comparison - ${layer}` : 'Impurity Comparison'">
                    <div v-if="isLoading">
                        <span class="bi bi-hourglass-split"></span>
                        Comparing...
                    </div>
                    <div v-else-if="error" class="text-danger">{{ error }}</div>
                    <div v-else-if="! plots.length" class="text-muted">
                        {{ isViewing
                            ? 'The impurity simulations have not been run.'
                            : 'Run both impurity simulations to compare them.' }}
                    </div>
                    <div v-for="(classes, k) in classesByWaste" v-bind:key="k" class="mb-3">
                        <div class="fw-bold">NRC class, {{ CLASS_TITLES[k] }}</div>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Time after shutdown</th>
                                    <th>Max impurities</th>
                                    <th>No impurities</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="c in classes"
                                    v-bind:key="c.coolingSeconds"
                                    v-bind:class="{ 'table-warning': c.max.nrcClass !== c.min.nrcClass }"
                                >
                                    <td>{{ coolingLabel(c.coolingSeconds) }}</td>
                                    <td>{{ classLabel(c.max) }}</td>
                                    <td>{{ classLabel(c.min) }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div v-if="hasSameScaledClasses()" class="mb-3">
                        The structure scaled waste disposal rating gives the same classes.
                    </div>
                    <div v-if="plots.length" class="text-muted small mb-3">
                        NRC 10 CFR 61.55 class; highlighted rows change class.
                        "Fetter &gt; 1" means the Fetter et al. (1990) rating is over 1.
                        Each plot shows the values with the impurities at their maximum
                        (solid) and with none (dashed), and below, their ratio (×1 is no
                        difference). The ratio is left out where both values are
                        negligible: waste ratings below 0.01, which can't change the class.
                    </div>
                </VCortexCard>
            </div>
        </div>
        <!-- as VNeutronics.vue's reports: 1 across on a small window, 2, or 3 on a wide one -->
        <div v-if="plots.length" class="row">
            <VCol
                v-for="p in plots"
                v-bind:key="p.name"
                v-bind:maxCols="3"
            >
                <VCard
                    v-bind:viewName="impurityReport(neutronics, 'max')"
                    v-bind:title="p.title"
                    v-bind:canFullScreen="true"
                >
                    <img v-bind:src="p.image" class="img-fluid" v-bind:alt="p.title"/>
                </VCard>
            </VCol>
        </div>
    </div>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCol from '@/components/layout/VCol.vue';
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VRunSim from '@/components/VRunSim.vue';
 import { appState } from '@/services/appstate.js';
 import { computed, onUnmounted, reactive, ref, watch } from 'vue';
 import { db } from '@/apps/cortex/db.js';
 import { impurityReport } from '@/apps/cortex/reports.js';
 import { useRoute } from 'vue-router';
 import { util } from '@/services/util.js';

 const props = defineProps({
     materialId: String,
     // neutronics report, e.g. hcpbSlabAnimation
     neutronics: String,
     // the material's components: material_component_name, target_pct, min_pct, max_pct
     components: Array,
     // summary sims of the impurity reports: max and min, undefined if not run
     runs: Object,
 });
 const emit = defineEmits(['simCompleted']);

 const DAY = 24 * 3600;
 // POSIT: sirepo.template.cortex _SECONDS_PER_YEAR
 const YEAR = 365 * DAY;
 // POSIT: the waste keys of sirepo.template.cortex _IMPURITY_PLOTS
 const CLASS_TITLES = {
     waste: 'waste disposal rating',
     waste_struct_scaled: 'structure scaled waste disposal rating',
 };
 const RUNS = [
     { impurity: 'max', title: 'Max Impurities Simulation' },
     { impurity: 'min', title: 'No Impurities Simulation' },
 ];
 const error = ref('');
 const isLoaded = appState.isLoadedRef;
 const isLoading = ref(false);
 // a public (featured) material is viewed by its id, not the owner's sim
 const isViewing = useRoute().name === 'view';
 // by key of CLASS_TITLES
 const classesByWaste = ref({});
 const layer = ref('');
 const plots = ref([]);
 // VRunSim's state of each run
 const sims = reactive({ max: {}, min: {} });

 // POSIT: the balance in sirepo.template.cortex _impurity_components
 const balance = computed(() => {
     const b = props.components.filter((c) => ! isImpurity(c));
     return b.length
         ? b.reduce((x, c) => c.target_pct > x.target_pct ? c : x).material_component_name
         : '';
 });

 // POSIT: sirepo.template.cortex _impurity_components
 const isImpurity = (c) => c.min_pct === 0 && c.max_pct > 0;

 const impurities = computed(() => props.components.filter(isImpurity));

 // POSIT: sirepo.template.cortex stateless_compute_impurity_comparison
 // leaves out the structure scaled classes if they are the same
 const hasSameScaledClasses = () => plots.value.some((p) => p.name === 'waste_struct_scaled')
     && ! classesByWaste.value.waste_struct_scaled;

 const classLabel = (c) => c.nrcClass + (c.fetterExceeds ? ' (Fetter > 1)' : '');

 const coolingLabel = (seconds) => {
     if (seconds < 2 * DAY) {
         return '1 day';
     }
     const y = Math.round(seconds / YEAR);
     return y === 1 ? '1 year' : `${y} years`;
 };

 const compare = async () => {
     revokeImages();
     classesByWaste.value = {};
     plots.value = [];
     error.value = '';
     if (! (props.runs.max && props.runs.min)) {
         return;
     }
     isLoading.value = true;
     try {
         const r = await db.impurityComparison(props.materialId, isViewing, props.neutronics);
         if (r.error) {
             error.value = r.error;
             return;
         }
         layer.value = r.layer;
         classesByWaste.value = r.classes;
         plots.value = r.plots.map((x) => ({
             name: x.name,
             title: x.title,
             image: URL.createObjectURL(new Blob([new Uint8Array(x.png)], { type: 'image/png' })),
         }));
     }
     catch (e) {
         error.value = 'Unable to compare the simulations, please try again';
     }
     finally {
         isLoading.value = false;
     }
 };

 const revokeImages = () => {
     for (const p of plots.value) {
         URL.revokeObjectURL(p.image);
     }
 };

 onUnmounted(revokeImages);

 // as VNeutronicsSim, a run is complete when it has a frame and reports
 for (const r of RUNS) {
     watch(() => sims[r.impurity].frameCount, () => {
         if (sims[r.impurity].frameCount && sims[r.impurity].reports) {
             emit('simCompleted');
         }
     });
 }

 // when either run completes, VNeutronics reloads the summary
 watch(
     () => [props.neutronics, props.runs.max?.completed, props.runs.min?.completed],
     compare,
     { immediate: true },
 );
</script>
