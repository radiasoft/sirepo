<template>
    <div class="row">
        <div class="col-lg-4">
            <VCortexCard title="Cost Inputs">
                <div class="mb-3">
                    <label class="form-label" for="sr-cost-qty">Production Quantity</label>
                    <input
                        id="sr-cost-qty"
                        type="text"
                        inputmode="numeric"
                        autocomplete="off"
                        class="form-control text-end"
                        v-bind:class="{'sr-invalid': ! isValidQty()}"
                        v-model="productionQty"
                    />
                </div>
                <div class="mb-3">
                    <div class="d-flex">
                        <div class="form-label flex-grow-1">Fabrication Process</div>
                        <div v-if="selectedProcesses.length" class="form-label sr-cost-cmp">Compatibility Factor</div>
                    </div>
                    <div
                        class="d-flex align-items-center mb-1"
                        v-for="p in processNames"
                        v-bind:key="p"
                    >
                        <div class="form-check mb-0 flex-grow-1">
                            <input
                                type="checkbox"
                                class="form-check-input"
                                v-bind:id="`sr-cost-process-${p}`"
                                v-bind:value="p"
                                v-model="selectedProcesses"
                            />
                            <label class="form-check-label" v-bind:for="`sr-cost-process-${p}`">{{ p }}</label>
                        </div>
                        <input
                            v-if="selectedProcesses.includes(p)"
                            type="text"
                            inputmode="decimal"
                            autocomplete="off"
                            class="form-control form-control-sm text-end sr-cost-cmp"
                            v-bind:class="{'sr-invalid': ! isValidCmp(p)}"
                            v-bind:aria-label="`${p} compatibility factor`"
                            v-model="cmp[p]"
                        />
                    </div>
                    <div v-if="selectedProcesses.length" class="form-text">
                        Compatibility factor: how costly this material is to process
                        with each method, relative to an ideal material (1.0).
                        Use values above 1.0 for materials that are harder to process,
                        e.g. 2.0 doubles that process's fabrication cost.
                    </div>
                </div>
                <button
                    type="button"
                    class="btn btn-outline-primary"
                    v-bind:disabled="! selectedProcesses.length || ! isValidQty() || ! selectedProcesses.every(isValidCmp) || isCalculating"
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
                    </tbody>
                </table>
            </VCortexCard>
        </div>
        <div class="col-lg-8">
            <VCortexCard>
                <ul class="nav nav-tabs mb-3">
                    <li class="nav-item" v-for="t in tabs" v-bind:key="t">
                        <button
                            type="button"
                            class="nav-link"
                            v-bind:class="{ active: t === selectedTab }"
                            v-on:click="selectedTab = t"
                        >
                            {{ t }}
                        </button>
                    </li>
                </ul>
                <div v-if="selectedTab === tabs[0]">
                    <div v-if="isCalculating">
                        <span class="bi bi-hourglass-split"></span>
                        Calculating...
                    </div>
                    <div v-else-if="result">
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
                    </div>
                </div>
                <div v-else>
                    <div class="lead mb-2">Default Manufacturing Process: {{ defaultProcess.name }}</div>
                    <p>{{ defaultProcess.intro }}</p>
                    <ul>
                        <li v-for="s in defaultProcess.steps" v-bind:key="s.name">
                            <strong>{{ s.name }}:</strong> {{ s.description }}
                        </li>
                    </ul>
                    <p>{{ defaultProcess.rationale }}</p>
                    <p>
                        <strong>Important:</strong> The process chain is meant to be representative
                        rather than exact. This is appropriate during concept development and
                        alternative analysis, where the goal is a reasonable estimate of
                        manufacturing steps and cost, not a qualified production route. A final
                        design may add, remove or change steps.
                    </p>
                    <p>{{ defaultProcess.responsibility }}</p>
                    <p class="mb-0">
                        Reference: {{ defaultProcess.reference }}
                        <a v-bind:href="defaultProcess.doi" target="_blank">{{ defaultProcess.doi }}</a>
                    </p>
                </div>
            </VCortexCard>
            <VCard
                v-if="chartImage && ! isCalculating"
                viewName="costChart"
                v-bind:canFullScreen="true"
                v-bind:downloadActions="chartDownloadActions"
            >
                <VReportImage v-bind:image="chartImage" alt="Cost breakdown chart" />
                <div class="form-text">
                    Total cost by category (left), with the Material segment zoomed in
                    to show its cost broken down by element (right).
                </div>
            </VCard>
            <VCard
                v-if="curveImage && ! isCalculating"
                viewName="costCurveChart"
                v-bind:canFullScreen="true"
                v-bind:downloadActions="curveDownloadActions"
            >
                <VReportImage v-bind:image="curveImage" alt="Fabrication cost vs. production quantity chart" />
                <div class="form-text">
                    Fabrication cost vs. production quantity for each process. Solid lines
                    use this material and this geometry; dashed lines use an ideal material
                    with an ideal geometry (Compatibility Factor = 1). The dotted vertical
                    line marks the entered production quantity.
                </div>
            </VCard>
        </div>
    </div>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VReportImage from '@/apps/cortex/VReportImage.vue';
 import { db } from '@/apps/cortex/db.js';
 import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
 import { useRoute } from 'vue-router';
 import { util } from '@/services/util.js';

 const props = defineProps({
     materialId: String,
     materialName: String,
     isPlasmaFacing: Boolean,
 });

 // fixed set of tea fabrication processes (sirepo/sim_api/cortex/tea_cost.py PROCESS_NAMES)
 const processNames = [
     'Cold Rolling',
     'Hot Rolling',
     'CNC',
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

 // descriptions of the default processes (selectedProcesses) for each geometry
 const defaultProcessFirstWall = {
     name: 'First Wall',
     intro: 'The default manufacturing process uses five standard industrial steps:',
     steps: [
         {name: 'Hot rolling', description: 'makes the starting plate stock'},
         {name: 'Cold rolling / cold bending', description: 'forms the plates to the required curvature'},
         {name: 'CNC machining', description: 'cuts the cooling-channel grooves and final geometry'},
         {name: 'Electron beam (EB) welding', description: 'seals the tube-and-plate assembly'},
         {name: 'Hot isostatic pressing (HIP)', description: 'diffusion-bonds the tubes to the plates to form the finished component'},
     ],
     rationale: 'These steps represent the fabrication route in Commin et al. (2013) for blanket first walls. In that route, tubes of the required cross-section are embedded between two grooved plates, sealed by EB welding and consolidated by HIP. Commin et al. chose the route because it relies only on standard, industrially available processes, which keeps it cost-effective.',
     responsibility: 'This process is given as a representative reference route only. The user is responsible for checking that the chosen material can be manufactured this way. That includes its suitability for hot and cold rolling, its machinability, its weldability by electron beam, its compatibility with HIP diffusion bonding, and whether it is available in the required product forms.',
     reference: 'L. Commin, M. Rieth, B. Dafferner, H. Zimmermann, D. Bolich, S. Baumgärtner, R. Ziegler, S. Dichiser, T. Fabry, S. Fischer, W. Hildebrand, O. Palussek, H. Ritz, A. Sponda, "A fail–safe and cost effective fabrication route for blanket First Walls," Journal of Nuclear Materials 442 (1–3) (2013) 538–541.',
     doi: 'https://doi.org/10.1016/j.jnucmat.2013.07.043',
 };
 const defaultProcessPlasmaFacing = {
     name: 'Plasma-Facing Surface',
     intro: 'The default process for the plasma-facing surface uses:',
     steps: [
         {name: 'Spray Deposition', description: 'deposits a functionally graded tungsten/steel coating directly onto the substrate'},
     ],
     rationale: 'These steps represent the coating route in Grammes et al. (2023) for the DEMO first wall. Vacuum plasma spraying (VPS) lays down a functionally graded layer about 1.2 mm thick, in which the tungsten content rises steadily from the steel substrate to the surface, and then a pure tungsten top layer about 0.8 mm thick, for about 2 mm in total. The graded interlayer reduces the thermal-expansion mismatch between tungsten and steel. Grammes et al. picked VPS because it produces the required material gradient with good microstructural quality at that coating thickness. They also showed it scales toward industrial production, coating plates up to 500 × 250 mm² that already had cooling channels.',
     responsibility: 'This process is given as a representative reference route only. The user is responsible for checking that the chosen coating and substrate materials can be manufactured this way. That includes whether the coating powder can be vacuum plasma sprayed, whether the coating and substrate are compatible (thermal expansion, bonding and diffusion), whether the required coating thickness and grading can be reached, and whether the coating will hold up under the intended thermal and plasma loads.',
     reference: 'T. Grammes, T. Emmerich, D. Qu, O. Heinze, R. Vaßen, J. Aktaa, "Functionally graded tungsten/EUROFER coating for DEMO first wall: From laboratory to industrial production," Fusion Engineering and Design 188 (2023) 113430.',
     doi: 'https://doi.org/10.1016/j.fusengdes.2023.113430',
 };
 const defaultProcess = computed(() => props.isPlasmaFacing ? defaultProcessPlasmaFacing : defaultProcessFirstWall);

 const tabs = ['Manufacturing Cost Summary', 'Fabrication Process Documentation'];
 const selectedTab = ref(tabs[0]);

 const chartImage = ref(null);
 // material/process compatibility cost coefficient per process, 1.0 is ideal
 const cmp = reactive(Object.fromEntries(processNames.map((p) => [p, 1.0])));
 const curveImage = ref(null);
 const error = ref('');
 const isCalculating = ref(false);
 const productionQty = ref(10);
 const result = ref(null);
 const route = useRoute();
 // a public (featured) material: starts from the owner's saved cost inputs,
 // which may be changed here but aren't saved
 const isPublic = route.name === 'view';
 // default reference routes, in fabrication order: vacuum plasma sprayed
 // W/steel coating for plasma-facing (Grammes et al. 2023), rolled,
 // machined, EB welded and HIP'd plates for first wall (Commin et al. 2013)
 const selectedProcesses = ref(
     props.isPlasmaFacing
         ? ['Spray Deposition']
         : ['Hot Rolling', 'Cold Rolling', 'CNC', 'Electron Beam', 'HIP']
 );

 const revokeImages = () => {
     for (const i of [chartImage, curveImage]) {
         if (i.value) {
             URL.revokeObjectURL(i.value);
             i.value = null;
         }
     }
 };

 const toImage = (png) => URL.createObjectURL(
     new Blob([new Uint8Array(png)], {type: 'image/png'})
 );

 // text inputs, so values may be any string; Number() rejects trailing
 // garbage (e.g. "1.2x") which parseFloat() would accept
 const toNumber = (value) => String(value).trim() === '' ? NaN : Number(value);

 const cmpValue = (process) => toNumber(cmp[process]);

 const isValidCmp = (process) => cmpValue(process) > 0;

 const qtyValue = () => toNumber(productionQty.value);

 const isValidQty = () => Number.isInteger(qtyValue()) && qtyValue() > 0;

 const formatCost = (value) => {
     return `$${Number(value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
 };

 const downloadChart = () => {
     util.downloadPNG({
         image: chartImage.value,
         y_label: `${props.materialName || 'Material'} Cost Breakdown`,
     });
 };

 const downloadCurve = () => {
     util.downloadPNG({
         image: curveImage.value,
         y_label: `${props.materialName || 'Material'} Fabrication Cost vs Production Quantity`,
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

 const curveDownloadActions = computed(() => [
     {
         onClick: downloadCurve,
         label: 'Download PNG',
     },
 ]);

 const calculate = async () => {
     error.value = '';
     isCalculating.value = true;
     try {
         const r = await db.calculateCost(
             props.materialId,
             isPublic,
             selectedProcesses.value,
             Object.fromEntries(selectedProcesses.value.map((p) => [p, cmpValue(p)])),
             qtyValue(),
         );
         if (r.error) {
             error.value = r.error;
             result.value = null;
             return;
         }
         result.value = r;
         revokeImages();
         chartImage.value = toImage(r.chart_png);
         curveImage.value = toImage(r.curve_png);
     }
     finally {
         isCalculating.value = false;
     }
 };

 onMounted(async () => {
     const i = await db.loadCostInput(props.materialId, isPublic);
     if (i) {
         selectedProcesses.value = i.processes;
         Object.assign(cmp, i.cmp);
         productionQty.value = i.production_qty;
     }
     await calculate();
 });

 onUnmounted(revokeImages);
</script>

<style scoped>
 .sr-cost-cmp {
     width: 8em;
 }
</style>
