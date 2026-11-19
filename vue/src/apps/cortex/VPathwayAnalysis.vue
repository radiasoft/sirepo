<template>
    <div class="row">
        <div class="col-lg-4">
            <VCortexCard title="Analysis">
                <div class="mb-3">
                    <label class="form-label" for="sr-pathway-metric">Metric</label>
                    <select
                        id="sr-pathway-metric"
                        class="form-select"
                        v-model="metric"
                    >
                        <option
                            v-for="m in METRICS"
                            v-bind:key="m.value"
                            v-bind:value="m.value"
                        >{{ m.label }}</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label" for="sr-pathway-cooling">Time After Shutdown</label>
                    <select
                        id="sr-pathway-cooling"
                        class="form-select"
                        v-model="coolingSeconds"
                    >
                        <option
                            v-for="c in COOLING_TIMES"
                            v-bind:key="c.value"
                            v-bind:value="c.value"
                        >{{ c.label }}</option>
                    </select>
                </div>
                <div class="mb-3">
                    <div class="form-label">Origins</div>
                    <VTabs
                        v-bind:items="ORIGINS"
                        v-bind:pills="true"
                        v-model="origins"
                    />
                </div>
                <button
                    type="button"
                    class="btn btn-outline-primary"
                    v-bind:disabled="isRunning"
                    v-on:click="run"
                >
                    Run Analysis
                </button>
                <div v-if="error" class="text-danger mt-3">{{ error }}</div>
                <div class="text-muted small mt-3">
                    Attributes the metric of the layer made of this material,
                    at the time after shutdown, to the elements or nuclides in
                    the layer before irradiation.
                </div>
            </VCortexCard>
        </div>
        <div class="col-lg-8">
            <VCortexCard title="Origins">
                <div v-if="isRunning">
                    <span class="bi bi-hourglass-split"></span>
                    Analyzing...
                </div>
                <div v-else-if="result">
                    <div class="mb-2">
                        <b>{{ metricLabel(result.metric) }}</b>
                        of the {{ layerLabel(result.layer) }} layer,
                        {{ coolingLabel(result.coolingSeconds) }} after shutdown:
                        {{ formatValue(result.total) }} {{ result.units }}
                    </div>
                    <div class="mb-2">
                        Waste classification: {{ result.wasteClass }}
                    </div>
                    <div class="fw-bold mt-3">Original components</div>
                    <div class="text-muted small">
                        The share of the {{ metricLabel(result.metric).toLowerCase() }}
                        that comes from each {{ result.byElement ? 'element' : 'nuclide' }}
                        in the layer before irradiation.
                    </div>
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>{{ result.byElement ? 'Element' : 'Nuclide' }}</th>
                                <th class="text-end">Contribution</th>
                                <th class="text-end">{{ result.units || 'Value' }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="r in result.rows" v-bind:key="r.name">
                                <td>{{ r.name }}</td>
                                <td class="text-end">{{ r.percent.toFixed(2) }}%</td>
                                <td class="text-end">{{ formatValue(r.value) }}</td>
                            </tr>
                        </tbody>
                    </table>
                    <div class="fw-bold mt-3">Radionuclides</div>
                    <div class="text-muted small">
                        The nuclides which carry the
                        {{ metricLabel(result.metric).toLowerCase() }}. Select one to
                        see how it was produced.
                    </div>
                    <table class="table table-sm table-hover">
                        <thead>
                            <tr>
                                <th>Nuclide</th>
                                <th class="text-end">Contribution</th>
                                <th class="text-end">{{ result.units || 'Value' }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <template v-for="r in result.radionuclides" v-bind:key="r.name">
                                <tr
                                    v-bind:class="{ 'sr-pathway-row': isNuclide(r.name), 'table-active': pathway.nuclide === r.name }"
                                    v-on:click="isNuclide(r.name) && selectNuclide(r.name)"
                                >
                                    <td>
                                        <span
                                            v-if="isNuclide(r.name)"
                                            class="bi"
                                            v-bind:class="pathway.nuclide === r.name ? 'bi-chevron-down' : 'bi-chevron-right'"
                                        ></span>
                                        {{ r.name }}
                                    </td>
                                    <td class="text-end">{{ r.percent.toFixed(2) }}%</td>
                                    <td class="text-end">{{ formatValue(r.value) }}</td>
                                </tr>
                                <tr v-if="pathway.nuclide === r.name">
                                    <td colspan="3" class="ps-4">
                                        <div v-if="pathway.isLoading">
                                            <span class="bi bi-hourglass-split"></span>
                                            Tracing...
                                        </div>
                                        <div v-else-if="pathway.error" class="text-danger">
                                            {{ pathway.error }}
                                        </div>
                                        <div v-else-if="pathway.result">
                                            <div>
                                                <b>Produced from:</b>
                                                {{ formatOrigins(pathway.result.origins) }}
                                            </div>
                                            <div v-if="pathway.result.chain.length > 1">
                                                <b>Main pathway:</b>
                                                <template
                                                    v-for="(c, i) in pathway.result.chain"
                                                    v-bind:key="i"
                                                >
                                                    <span v-if="c.channel" class="text-muted">
                                                        &rarr; {{ channelLabel(c.channel) }} &rarr;
                                                    </span>
                                                    {{ c.name }}
                                                </template>
                                            </div>
                                            <div v-else-if="pathway.result.chain.length">
                                                In the material from the start.
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                    <div v-if="result.skipped.length" class="text-muted small">
                        Not traced: {{ result.skipped.join(', ') }}
                    </div>
                </div>
                <div v-else class="text-muted">
                    Select a metric and run the analysis.
                </div>
            </VCortexCard>
        </div>
    </div>
</template>

<script setup>
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VTabs from '@/components/VTabs.vue';
 import { db } from '@/apps/cortex/db.js';
 import { reactive, ref, watch } from 'vue';
 import { useRoute } from 'vue-router';
 import { util } from '@/services/util.js';

 const props = defineProps({
     materialId: String,
     // report name, e.g. hcpbSlabAnimation
     neutronics: String,
 });

 const DAY = 24 * 3600;
 // POSIT: sirepo.template.cortex _SECONDS_PER_YEAR
 const YEAR = 365 * DAY;
 // POSIT: sirepo.template.cortex _PATHWAY_COOLING_SECONDS
 const COOLING_TIMES = [
     { value: DAY, label: '1 day' },
     { value: 7 * DAY, label: '1 week' },
     { value: YEAR / 12, label: '1 month' },
     { value: YEAR, label: '1 year' },
     { value: 10 * YEAR, label: '10 years' },
     { value: 100 * YEAR, label: '100 years' },
     { value: 1000 * YEAR, label: '1000 years' },
 ];
 // POSIT: sirepo.template.cortex _PATHWAY_METRICS
 const METRICS = [
     { value: 'activity', label: 'Activity' },
     { value: 'decay_heat', label: 'Decay Heat' },
     { value: 'contact_dose', label: 'Contact Dose Rate' },
     { value: 'waste_disposal_rating', label: 'Waste Disposal Rating' },
 ];
 const ORIGINS = [
     { value: 'element', label: 'Elements' },
     { value: 'nuclide', label: 'Nuclides' },
 ];
 // waste classification, the time of the summary's activity and decay heat
 const coolingSeconds = ref(100 * YEAR);
 const error = ref('');
 const isRunning = ref(false);
 const metric = ref(METRICS[0].value);
 const origins = ref(ORIGINS[0].value);
 // production pathway of the selected radionuclide of result
 const pathway = reactive({ nuclide: null, isLoading: false, error: '', result: null });
 const result = ref(null);
 const route = useRoute();
 // a public (featured) material is viewed by its id, not the owner's sim
 const isPublic = route.name === 'view';

 // decay channels in the depletion chain
 const channelLabel = (channel) => ({
     alpha: 'α',
     beta: 'β⁻',
     'beta-': 'β⁻',
     'beta+': 'β⁺',
     ec: 'EC',
     'ec/beta+': 'EC/β⁺',
 }[channel] || channel);

 // the time of the depletion step used, which may differ from the one selected
 const coolingLabel = (seconds) => {
     const c = COOLING_TIMES.find((c) => Math.abs(c.value - seconds) < 1);
     if (c) {
         return c.label;
     }
     return seconds < YEAR
         ? `${(seconds / DAY).toPrecision(3)} days`
         : `${(seconds / YEAR).toPrecision(3)} years`;
 };

 const formatOrigins = (origins) => {
     const o = origins.filter((x) => x.percent >= 0.01).slice(0, 3);
     return o.length
         ? o.map((x) => `${x.name} ${x.percent.toFixed(2)}%`).join(', ')
         : 'not attributed to the original components';
 };

 const formatValue = (value) => util.formatExponential(value) || '0';

 // the row which sums the rest isn't a nuclide
 const isNuclide = (name) => name !== 'Other';

 // POSIT: the material names in slab.py.jinja's cell_material_map.csv
 const layerLabel = (layer) => layer.replace(/_/g, ' ');

 const metricLabel = (value) => METRICS.find((m) => m.value === value).label;

 const run = async () => {
     error.value = '';
     isRunning.value = true;
     try {
         const b = origins.value === 'element';
         const r = await db.pathwayAnalysis(
             props.materialId,
             isPublic,
             props.neutronics,
             metric.value,
             b,
             coolingSeconds.value,
         );
         if (r.error) {
             error.value = r.error;
             result.value = null;
             return;
         }
         r.byElement = b;
         // the nuclide pathways are for the same time as the result
         r.coolingRequest = coolingSeconds.value;
         resetPathway();
         result.value = r;
     }
     catch (e) {
         error.value = 'Unable to run the analysis, please try again';
         result.value = null;
     }
     finally {
         isRunning.value = false;
     }
 };

 const resetPathway = () => {
     Object.assign(pathway, { nuclide: null, isLoading: false, error: '', result: null });
 };

 const selectNuclide = async (nuclide) => {
     if (pathway.nuclide === nuclide) {
         resetPathway();
         return;
     }
     resetPathway();
     pathway.nuclide = nuclide;
     pathway.isLoading = true;
     try {
         const r = await db.pathwayNuclide(
             props.materialId,
             isPublic,
             props.neutronics,
             nuclide,
             result.value.coolingRequest,
         );
         // another nuclide may have been selected while this one was traced
         if (pathway.nuclide !== nuclide) {
             return;
         }
         if (r.error) {
             pathway.error = r.error;
             return;
         }
         pathway.result = r;
     }
     catch (e) {
         if (pathway.nuclide === nuclide) {
             pathway.error = 'Unable to trace the nuclide, please try again';
         }
     }
     finally {
         if (pathway.nuclide === nuclide) {
             pathway.isLoading = false;
         }
     }
 };

 watch(() => props.neutronics, () => {
     error.value = '';
     resetPathway();
     result.value = null;
 });
</script>

<style scoped>
 .sr-pathway-row {
     cursor: pointer;
 }
</style>
