<template>
    <VCol>
        <VCard viewName="simulationStatus" v-bind:title="title">
            <div class="row">
                <div class="col-sm-7" v-if="isLoaded">
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
 import { nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';

 const props = defineProps({
     materialId: String,
     neutronics: String,
     title: String,
 });
 const isLoaded = appState.isLoadedRef;
 const reportsBySection = reactive({});
 const sections = {
     steady_state: 'Steady State',
     flux: 'ParticleFluxes',
     time_dependent: 'Time-Dependent Responses',
 };
 const sim = ref({});
 let reportData;
 let simId;

 const loadFromDatabase = async () => {
     const r = await requestSender.sendRequest("cortexSim", {
         op_name: 'synchronize',
         op_args: {
             material_id: props.materialId,
         },
     });
     reportData = r.reports;
     simId = r.simulationId;
 };

 const rebuildReports = async () => {
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
     if (Object.keys(reportsBySection).length) {
         if (isLoaded.value) {
             appState.clearModels();
         }
     }
     else {
         if (! isLoaded.value) {
             await appState.loadModels(simId);
         }
     }
 };

 onMounted(async () => {
     await loadFromDatabase();
     await rebuildReports();
 });

 onUnmounted(() => {
     if (isLoaded.value) {
         appState.clearModels();
     }
 });

 watch(() => sim.value.frameCount, async () => {
     if (sim.value.reports) {
         await loadFromDatabase();
     }
     await rebuildReports();
 });

 watch(() => props.neutronics, () => {
     sim.value = {};
     appState.clearModels();
     // isLoaded.value is not updated immediately after clearModels()
     nextTick(async () => {
         await rebuildReports();
     });
 });

</script>
