<template>
    <div class="col-md-8 col-xl-6">
        <VCard viewName="simulationStatus" v-bind:title="title">
            <div class="row">
                <div class="col-sm-7" v-if="isReady">
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
                    <div v-if="showRunSim()">
                        <VNeutronicsSim
                            v-bind:materialId="materialId"
                            v-bind:neutronics="neutronics"
                            v-on:simCompleted="loadAndRebuild()"
                        />
                    </div>
                </div>
                <div class="col-sm-5" v-if="neutronics === 'slabAnimation'">
                    <img class="img-fluid" v-bind:src="slabUrl" alt="Slab" style="max-height: 250px"/>
                </div>
            </div>
        </VCard>
    </div>
    <VCortexCard v-bind:title="sections[section]" v-for="section in Object.keys(reportsBySection)">
        <div class="row">
            <VCol v-for="report in reportsBySection[section]" v-bind:key="report.trackBy">
                <VCard
                    v-bind:viewName="report.viewName"
                    v-bind:title="report.title"
                    v-bind:canFullScreen="true"
                    v-bind:downloadActions="report.reportData.downloadActions"
                >
                    <VFramePlot
                        v-bind:modelName="report.modelName"
                        v-bind:reportData="report.reportData"
                    ></VFramePlot>
                </VCard>
            </VCol>
        </div>
    </VCortexCard>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCol from '@/components/layout/VCol.vue';
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VFramePlot from '@/components/plot/VFramePlot.vue';
 import VNeutronicsSim from '@/apps/cortex/VNeutronicsSim.vue';
 import slabUrl from '@/assets/cortex/slab.png';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, reactive, ref, watch } from 'vue';
 import { useRoute } from 'vue-router';
 import { util } from '@/services/util.js';

 const props = defineProps({
     materialId: String,
     neutronics: String,
     title: String,
 });
 const reportsBySection = reactive({});
 const sections = {
     steady_state: 'Steady State',
     flux: 'ParticleFluxes',
     time_dependent: 'Time-Dependent Responses',
 };
 let summary;
 const hasPlots = ref(false);
 const isReady = ref(false);
 const route = useRoute();
 const simSummary = ref(null);

 const showRunSim = () => {
     if (route.name === "view" || route.name === "admin-view") {
         return false;
     }
     if (isSimOutOfDate()) {
         return true;
     }
     return ! hasPlots.value;
 };

 const isSimOutOfDate = () => {
     if (! (summary && summary.sim[props.neutronics])) {
         return true;
     }
     return summary.sim[props.neutronics].version !== summary.sim[props.neutronics].current_version;
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
         reportsBySection[r.meta.section].push({
             title: r.panelTitle,
             modelName: r.meta.model,
             viewName: r.meta.model,
             trackBy: r.meta.model + r.meta.stat,
             reportData: r,
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
 };

 const loadAndRebuild = async () => {
     summary = await db.loadSummary(props.materialId, route.name);
     await rebuildReports();
 };

 onMounted(async () => {
     await loadAndRebuild();
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
