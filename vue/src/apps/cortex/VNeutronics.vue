<template>
    <VCol v-if="isLoaded">
        <VCard viewName="simulationStatus" v-bind:title="title">
            <div class="row">
                <div class="col-sm-7" v-if="! hasReportData">
                    <VRunSim v-bind:sim="sim" v-bind:viewName="neutronics"></VRunSim>
                </div>
                <div class="col-sm-5" v-if="neutronics == 'slabAnimation'">
                    <img  class="img-fluid" v-bind:src="slabUrl" alt="Slab" />
                </div>
            </div>
        </VCard>
    </VCol>
    <VCortexCard v-bind:title="sections[section]" v-for="section in Object.keys(reportsBySection)">
        <div class="row">
            <VCol v-for="report in reportsBySection[section]" v-bind:key="report.trackBy">
                <VCard
                    v-bind:viewName="report.viewName"
                    v-bind:title="report.title"
                    v-bind:canFullScreen="true"
                    v-bind:downloadActions="report.downloadActions"
                >
                    <VFramePlot
                        v-bind:sim="sim"
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
 import VRunSim from '@/components/VRunSim.vue';
 import slabUrl from '@/assets/cortex/slab.png';
 import { appState } from '@/services/appstate.js';
 import { onMounted, onUnmounted, reactive, ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';

 const props = defineProps({
     materialId: String,
     neutronics: String,
     title: String,
 });
 const isLoaded = ref(false);
 const reportsBySection = reactive({});
 const sections = {
     steady_state: 'Steady State',
     flux: 'ParticleFluxes',
     time_dependent: 'Time-Dependent Responses',
 };
 const sim = ref({});
 let reportData;
 const hasReportData = ref(false);

 const rebuildReports = () => {
     hasReportData.value = false;
     if (reportData) {
         for (const r of reportData) {
             if (r.meta.model === props.neutronics) {
                 hasReportData.value = true;
                 break;
             }
         }
     }
     for (const v in sections) {
         reportsBySection[v] = [];
     }
     let i = 0;
     for (const r of reportData || []) {
         if (r.meta.model !== props.neutronics) {
             continue;
         }
         reportsBySection[r.meta.section].push({
             modelName: r.meta.model,
             stat: r.meta.stat,
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
 };

 const loadFromDatabase = async () => {
     const r = await requestSender.sendRequest("cortexSim", {
         op_name: 'synchronize',
         op_args: {
             material_id: props.materialId,
         },
     });
     reportData = r.reports;
     await appState.loadModels(r.simulationId);
     isLoaded.value = true;
 };

 onMounted(async () => {
     await loadFromDatabase();
     rebuildReports();
 });

 onUnmounted(() => {
     isLoaded.value = false;
     hasReportData.value = false;
     appState.clearModels();
 });

 watch(() => sim.value.reports, async () => {
     if (sim.value.reports) {
         appState.clearModels();
         await loadFromDatabase();
     }
     rebuildReports();
 });

 watch(() => props.neutronics, rebuildReports);

</script>
