<template>
    <div class="col-md-12 col-xxl-8">
        <VCard
            v-if="isReady"
            v-bind:viewName="isViewing() ? 'simulationStatus' : 'simulationSettings'"
            v-bind:title="title"
        >
            <div v-if="hasPlots" class="float-end">
                <button
                    class="btn btn-sm btn-outline-secondary"
                    v-on:click="downloadOutputZip"
                    title="Download output files"
                >
                    <span class="bi bi-download"></span>
                </button>
            </div>
            <div class="row">
                <div class="col-lg-4">
                    <div v-if="simSummary">
                        <div>
                            <b>Completed:</b> {{ util.formatDate(simSummary.completed) }}
                            <b>Version:</b> {{ simSummary.version }}
                        </div>
                        <div v-if="isSimOutOfDate()" class="mb-3">
                            This simulation was run with an older model.
                        </div>
                        <div v-else>
                            This simulation was run with the most recent model.
                        </div>
                    </div>
                    <div v-else-if="isLoadingPlots">
                        <span class="bi bi-hourglass-split"></span>
                        Loading plots...
                    </div>
                    <div v-if="! isViewing()" class="mt-3">
                        <VNeutronicsSim
                            v-bind:materialId="materialId"
                            v-bind:neutronics="neutronics"
                            v-on:simCompleted="loadAndRebuild()"
                            v-on:simStarted="onSimStarted()"
                        />
                    </div>
                </div>
                <div class="col-lg-8">
                    <div
                        v-if="simSummary && simSummary.results && simSummary.results.length"
                        class="fw-bold mb-2"
                    >
                        Damage, gas production &amp; activation per layer
                    </div>
                    <table
                        v-if="simSummary && simSummary.results && simSummary.results.length"
                        class="table table-sm"
                    >
                        <thead>
                            <tr>
                                <th>Layer</th>
                                <th
                                    v-for="col in summaryCols"
                                    v-bind:key="col.name"
                                    class="text-end"
                                >
                                    {{ col.heading }}
                                    <div class="sr-subheading">{{ col.subheading }}</div>
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr
                                v-for="row in simSummary.results"
                                v-bind:key="row.layer"
                            >
                                <td>{{ row.layer }}<span
                                    v-if="layerMaterial(row)"
                                    class="sr-subheading"
                                >&nbsp;{{ layerMaterial(row) }}</span></td>
                                <td
                                    v-for="col in summaryCols"
                                    v-bind:key="col.name"
                                    class="text-end"
                                >{{ formatValue(row, col) }}<span
                                    v-if="col.std && row[`${col.name}_std`] !== undefined && row[`${col.name}_std`] !== null"
                                    class="sr-subheading"
                                >&nbsp;&plusmn;&nbsp;{{ formatStd(row, col) }}</span></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </VCard>
    </div>
    <VCortexCard v-bind:title="sections[section]" v-for="section in Object.keys(reportsBySection)">
        <div class="row">
            <VCol
                v-for="report in reportsBySection[section]"
                v-bind:key="report.trackBy"
                v-bind:maxCols="3"
            >
                <VCard
                    v-bind:viewName="report.viewName"
                    v-bind:title="report.title"
                    v-bind:canFullScreen="true"
                    v-bind:downloadActions="report.downloadActions"
                >
                    <div v-if="report.error">{{ report.error }}</div>
                    <div v-if="report.image" v-bind:class="{ 'sr-slab-image': report.isStatic }">
                        <VReportImage
                            v-bind:image="report.image"
                            v-bind:alt="report.stat"
                        />
                    </div>
                </VCard>
            </VCol>
        </div>
    </VCortexCard>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCol from '@/components/layout/VCol.vue';
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VNeutronicsSim from '@/apps/cortex/VNeutronicsSim.vue';
 import VReportImage from '@/apps/cortex/VReportImage.vue';
 import slabUrl from '@/assets/cortex/slab.png';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, onUnmounted, reactive, ref, watch } from 'vue';
 import { useRoute } from 'vue-router';
 import { util } from '@/services/util.js';
 import { SUMMARY_COLUMNS, useSummary } from '@/apps/cortex/useSummary.js';

 const props = defineProps({
     materialId: String,
     materialName: String,
     isPlasmaFacing: Boolean,
     neutronics: String,
     title: String,
 });
 const reportsBySection = reactive({});
 const sections = {
     steady_state: 'Steady State',
     flux: 'Particle Fluxes',
     time_dependent: 'Time-Dependent Responses',
 };
 const summaryCols = SUMMARY_COLUMNS;
 const { formatValue, formatStd } = useSummary(3);
 let rebuildCounter = 0;
 let summary;
 const hasPlots = ref(false);
 const isLoadingPlots = ref(false);
 const isReady = ref(false);
 const route = useRoute();
 const simSummary = ref(null);

 const downloadOutputZip = async () => {
     const b = await db.loadOutputZip(props.materialId, props.neutronics);
     if (! b) {
         //TODO(pjm): error handling
         return;
     }
     const u = URL.createObjectURL(b);
     const a = document.createElement('a');
     a.href = u;
     a.download = util.downloadFilename(`${props.materialName} ${props.title}`, 'zip');
     a.click();
     URL.revokeObjectURL(u);
 };

 const layerMaterial = (row) => {
     if (row.layer === 'First Wall' && props.isPlasmaFacing) {
         return 'Eurofer';
     }
     if (row.layer === 'Armor' && ! props.isPlasmaFacing) {
         return 'Tungsten';
     }
     if (row.layer === 'Vacuum Vessel') {
         return 'SS316L(N)-IG';
     }
     return '';
 };

 const isSimOutOfDate = () => {
     if (! (summary && summary.sim[props.neutronics])) {
         return true;
     }
     return summary.sim[props.neutronics].version !== summary.sim[props.neutronics].current_version;
 };

 const isViewing = () => route.name === "view";

 const onSimStarted = () => {
     hasPlots.value = false;
     simSummary.value = null;
     for (const v in reportsBySection) {
         delete reportsBySection[v];
     }
 };

 const rebuildReports = async () => {
     for (const v in sections) {
         reportsBySection[v] = [];
     }
     let i = 0;
     for (const r of summary.plots) {
         if (r.meta.model !== props.neutronics) {
             continue;
         }
         if (r.title) {
             // only show the report title on panel
             r.panelTitle = r.title;
             r.title = "";
         }
         const p = {
             title: r.panelTitle,
             modelName: r.meta.model,
             viewName: r.meta.model,
             trackBy: r.meta.model + r.meta.stat,
             stat: r.meta.stat,
             // needed by util.downloadCSV(); .image is added later by loadImages()
             x_label: r.x_label,
             y_label: r.y_label,
             x_points: r.x_points,
             plots: r.plots,
         };
         p.downloadActions = util.reportDownloadActions(p);
         reportsBySection[r.meta.section].push(p);
     }
     if (reportsBySection.steady_state && reportsBySection.steady_state.length) {
         reportsBySection.steady_state.unshift({
             title: 'Geometry',
             viewName: props.neutronics,
             trackBy: 'geometry',
             stat: 'Slab',
             image: slabUrl,
             isStatic: true,
         });
     }
     for (const v in sections) {
         if (! reportsBySection[v].length) {
             delete reportsBySection[v];
         }
     }
     hasPlots.value = Boolean(Object.keys(reportsBySection).length);
     simSummary.value = summary.sim[props.neutronics];
     isReady.value = true;
     // does not await for images images to load
     rebuildCounter += 1;
     loadImages(rebuildCounter);
 };

 const loadAndRebuild = async () => {
     isLoadingPlots.value = true;
     try {
         const s = await db.loadSummary(props.materialId, isViewing());
         if (summary && s
             && summary?.sim[props.neutronics]?.completed === s?.sim[props.neutronics]?.completed) {
             // same summary, no rebuild required
             return;
         }
         summary = s;
         await rebuildReports();
     }
     finally {
         isLoadingPlots.value = false;
     }
 };

 const loadImages = async (counter) => {
     for (const s in sections) {
         if (reportsBySection[s]){
             for (const r of reportsBySection[s]) {
                 if (r.isStatic) {
                     continue;
                 }
                 r.error = '';
                 // stop loading if unloaded or rebuilt
                 if (hasPlots.value && counter === rebuildCounter) {
                     const b = await db.statImage(props.materialId, r.modelName, r.stat);
                     if (b) {
                         r.image = URL.createObjectURL(b);
                     }
                     else {
                         r.error ="Unable to load report";
                     }
                 }
             }
         }
     }
 };

 onMounted(async () => {
     await loadAndRebuild();
 });

 onUnmounted(() => {
     hasPlots.value = false;
 });

 watch(() => props.neutronics, async () => {
     hasPlots.value = false;
     isReady.value = false;
     simSummary.value = null;
     if (summary) {
         await rebuildReports();
     }
 });

</script>

<style scoped>
 /* match the plot report panels' image height (aspect ratio 1886 x 1410) */
 .sr-slab-image :deep(img) {
     width: 100%;
     height: auto;
     aspect-ratio: 1886 / 1410;
     object-fit: contain;
 }
</style>
