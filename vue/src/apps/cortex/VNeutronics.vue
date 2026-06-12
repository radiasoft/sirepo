<template>
    <div class="col-md-8 col-xl-6">
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
                <div class="col-sm-7">
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
                    <div v-if="! isViewing()" class="mt-3">
                        <VNeutronicsSim
                            v-bind:materialId="materialId"
                            v-bind:neutronics="neutronics"
                            v-on:simCompleted="loadAndRebuild()"
                        />
                    </div>
                </div>
                <div class="col-sm-5" v-if="neutronics.indexOf('SlabAnimation') > 0">
                    <img class="img-fluid" v-bind:src="slabUrl" alt="Slab" style="max-height: 250px"/>
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
                    <div v-if="report.image">
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

 const props = defineProps({
     materialId: String,
     materialName: String,
     neutronics: String,
     title: String,
 });
 const reportsBySection = reactive({});
 const sections = {
     steady_state: 'Steady State',
     flux: 'ParticleFluxes',
     time_dependent: 'Time-Dependent Responses',
 };
 let rebuildCounter = 0;
 let summary;
 const hasPlots = ref(false);
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

 const isSimOutOfDate = () => {
     if (! (summary && summary.sim[props.neutronics])) {
         return true;
     }
     return summary.sim[props.neutronics].version !== summary.sim[props.neutronics].current_version;
 };

 const isViewing = () => route.name === "view";

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
         reportsBySection[r.meta.section].push({
             title: r.panelTitle,
             modelName: r.meta.model,
             viewName: r.meta.model,
             trackBy: r.meta.model + r.meta.stat,
             stat: r.meta.stat,
             downloadActions: util.reportDownloadActions(r),
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
     const s = await db.loadSummary(props.materialId, isViewing());
     if (summary && s
         && summary?.sim[props.neutronics]?.completed === s?.sim[props.neutronics]?.completed) {
         // same summary, no rebuild required
         return;
     }
     summary = s;
     await rebuildReports();
 };

 const loadImages = async (counter) => {
     for (const s in sections) {
         if (reportsBySection[s]){
             for (const r of reportsBySection[s]) {
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
