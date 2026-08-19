<template>
    <div class="row">
        <div class="col-lg-4">
            <VCortexCard title="Cost Inputs">
                <div class="mb-3">
                    <label class="form-label" for="sr-cost-qty">Production Quantity</label>
                    <input
                        id="sr-cost-qty"
                        type="number"
                        min="1"
                        step="1"
                        class="form-control"
                        v-model.number="productionQty"
                    />
                </div>
                <div class="mb-3">
                    <div class="form-label">Fabrication Process</div>
                    <div
                        class="form-check"
                        v-for="p in processNames"
                        v-bind:key="p"
                    >
                        <input
                            type="checkbox"
                            class="form-check-input"
                            v-bind:id="`sr-cost-process-${p}`"
                            v-bind:value="p"
                            v-model="selectedProcesses"
                        />
                        <label class="form-check-label" v-bind:for="`sr-cost-process-${p}`">{{ p }}</label>
                    </div>
                </div>
                <button
                    type="button"
                    class="btn btn-outline-primary"
                    v-bind:disabled="! selectedProcesses.length || ! productionQty || isCalculating"
                    v-on:click="calculate"
                >
                    Calculate
                </button>
                <div v-if="error" class="text-danger mt-3">{{ error }}</div>
            </VCortexCard>
            <VCortexCard title="Cost Parameters">
                <table class="table table-sm mb-0">
                    <tbody>
                        <tr>
                            <td>Geometry</td>
                            <td class="text-end">{{ geometry.name }}</td>
                        </tr>
                        <tr>
                            <td>Section Thickness</td>
                            <td class="text-end">{{ geometry.section_thickness_mm }} mm</td>
                        </tr>
                        <tr>
                            <td>Volume</td>
                            <td class="text-end">{{ geometry.volume_mm3.toLocaleString('en-US') }} mm³</td>
                        </tr>
                        <tr>
                            <td>Shape Class</td>
                            <td class="text-end">{{ geometry.shape_class }}</td>
                        </tr>
                        <tr>
                            <td>Tolerance</td>
                            <td class="text-end">{{ geometry.tolerance_mm }} mm</td>
                        </tr>
                        <tr>
                            <td>Surface Finish</td>
                            <td class="text-end">{{ geometry.surface_finish_um_ra }} µm Ra</td>
                        </tr>
                        <tr>
                            <td>
                                Geometry Coefficients
                                <div class="sr-subheading">Cc, Cs, Ct, Cf</div>
                            </td>
                            <td class="text-end">1.0 (ideal)</td>
                        </tr>
                        <tr>
                            <td>
                                Material/Process Compatibility
                                <div class="sr-subheading">Cmp</div>
                            </td>
                            <td class="text-end">1.0 (ideal)</td>
                        </tr>
                    </tbody>
                </table>
            </VCortexCard>
        </div>
        <div class="col-lg-8" v-if="isCalculating || result">
            <VCortexCard v-if="isCalculating" title="Manufacturing Cost Summary">
                <span class="bi bi-hourglass-split"></span>
                Calculating...
            </VCortexCard>
            <VCortexCard v-else title="Manufacturing Cost Summary">
                <div v-if="result.warnings && result.warnings.length" class="text-warning mb-3">
                    <div v-for="(w, idx) in result.warnings" v-bind:key="idx">{{ w }}</div>
                </div>
                <table class="table table-sm">
                    <tbody>
                        <tr>
                            <td>Total Cost</td>
                            <td class="text-end">{{ formatCost(result.summary['Total cost']) }}</td>
                        </tr>
                        <tr>
                            <td>Unit Cost</td>
                            <td class="text-end">{{ formatCost(result.summary['Unit cost']) }} / kg</td>
                        </tr>
                        <tr>
                            <td>Mass</td>
                            <td class="text-end">{{ result.summary.Mass.toFixed(3) }} kg</td>
                        </tr>
                        <tr>
                            <td>Material Cost</td>
                            <td class="text-end">{{ formatCost(result.summary['Material cost']) }}</td>
                        </tr>
                        <tr>
                            <td>Processing Cost</td>
                            <td class="text-end">{{ formatCost(result.summary['Processing cost']) }}</td>
                        </tr>
                    </tbody>
                </table>
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Process</th>
                            <th class="text-end">Basic Cost</th>
                            <th class="text-end">Relative Cost</th>
                            <th class="text-end">Cost</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="p in result.summary.Processes"
                            v-bind:key="p.Process"
                        >
                            <td>{{ p.Process }}</td>
                            <td class="text-end">{{ formatCost(p.Pc) }}</td>
                            <td class="text-end">{{ p.Rc.toFixed(3) }}</td>
                            <td class="text-end">{{ formatCost(p.Cost) }}</td>
                        </tr>
                    </tbody>
                </table>
            </VCortexCard>
            <VCard
                v-if="chartImage && ! isCalculating"
                viewName="costChart"
                v-bind:canFullScreen="true"
                v-bind:downloadActions="chartDownloadActions"
            >
                <VReportImage v-bind:image="chartImage" alt="Cost breakdown chart" />
            </VCard>
        </div>
    </div>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VReportImage from '@/apps/cortex/VReportImage.vue';
 import { db } from '@/apps/cortex/db.js';
 import { computed, onMounted, onUnmounted, ref } from 'vue';
 import { useRoute } from 'vue-router';
 import { util } from '@/services/util.js';

 const props = defineProps({
     materialId: String,
     materialName: String,
     isPlasmaFacing: Boolean,
 });

 // fixed set of tea fabrication processes (sirepo/sim_api/cortex/tea_cost.py PROCESS_NAMES)
 const processNames = [
     'CNC',
     'Hot Rolling',
     'Cold Rolling',
     'HIP',
     'Electron Beam',
     'Diffusion Bonding',
     'Spray Deposition',
 ];

 // fixed geometry presets (sirepo/sim_api/cortex/tea_cost.py _GEOMETRY_ARMOR / _GEOMETRY_FIRST_WALL)
 const geometryArmor = {
     name: 'Plasma Facing Surface',
     volume_mm3: 3_000_000,
     section_thickness_mm: 2,
     shape_class: 'C1',
     tolerance_mm: 0.1,
     surface_finish_um_ra: 1,
 };
 const geometryFirstWall = {
     name: 'First Wall',
     volume_mm3: 45_000_000,
     section_thickness_mm: 30,
     shape_class: 'C1',
     tolerance_mm: 0.1,
     surface_finish_um_ra: 1,
 };
 const geometry = computed(() => props.isPlasmaFacing ? geometryArmor : geometryFirstWall);

 const chartImage = ref(null);
 const error = ref('');
 const isCalculating = ref(false);
 const productionQty = ref(10);
 const result = ref(null);
 const route = useRoute();
 // armor tiles are predominantly HIP'd (powder consolidation and bonding
 // to the substrate); first wall/structural components are predominantly
 // hot rolled plate/sheet stock
 const selectedProcesses = ref([props.isPlasmaFacing ? 'HIP' : 'Hot Rolling']);

 const formatCost = (value) => {
     return `$${Number(value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
 };

 const downloadChart = () => {
     util.downloadPNG({
         image: chartImage.value,
         y_label: `${props.materialName || 'Material'} Cost Breakdown`,
     });
 };

 const downloadSource = () => {
     util.downloadText(
         result.value.source_code,
         util.downloadFilename(props.materialName || 'material', 'py'),
     );
 };

 const chartDownloadActions = computed(() => [
     {
         onClick: downloadChart,
         label: 'Download PNG',
     },
     {
         onClick: downloadSource,
         label: 'Download Source',
     },
 ]);

 const calculate = async () => {
     error.value = '';
     isCalculating.value = true;
     try {
         const r = await db.calculateCost(
             props.materialId,
             route.name === 'view',
             selectedProcesses.value,
             productionQty.value,
         );
         if (r.error) {
             error.value = r.error;
             result.value = null;
             return;
         }
         result.value = r;
         if (chartImage.value) {
             URL.revokeObjectURL(chartImage.value);
         }
         chartImage.value = URL.createObjectURL(
             new Blob([new Uint8Array(r.chart_png)], {type: 'image/png'})
         );
     }
     finally {
         isCalculating.value = false;
     }
 };

 onMounted(async () => {
     if (route.name !== 'view') {
         const i = await db.loadCostInput(props.materialId);
         if (i) {
             selectedProcesses.value = i.processes;
             productionQty.value = i.production_qty;
         }
     }
     await calculate();
 });

 onUnmounted(() => {
     if (chartImage.value) {
         URL.revokeObjectURL(chartImage.value);
     }
 });
</script>
