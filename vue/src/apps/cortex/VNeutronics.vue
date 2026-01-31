<template>
    <VMasonry>
        <VCol v-if="isLoaded">
            <VCard viewName="simulationStatus" v-bind:title="title">
                <VRunSim v-bind:sim="sim" v-bind:viewName="neutronics"></VRunSim>
            </VCard>
        </VCol>
        <VCol v-for="report in sim.reports"">
            <VCard
                v-bind:viewName="report.viewName"
                v-bind:title="report.title"
                v-bind:canFullScreen="true"
                v-bind:downloadActions="report.downloadActions"
            >
                <VFramePlot v-bind:sim="sim" v-bind:modelName="report.modelName"></VFramePlot>
            </VCard>
        </VCol>
    </VMasonry>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCol from '@/components/layout/VCol.vue';
 import VFramePlot from '@/components/plot/VFramePlot.vue';
 import VMasonry from '@/components/layout/VMasonry.vue'
 import VRunSim from '@/components/VRunSim.vue';
 import { appState } from '@/services/appstate.js';
 import { onMounted, onUnmounted, ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';

 const props = defineProps({
     materialId: String,
     neutronics: String,
     title: String,
 });
 const isLoaded = ref(false);
 const sim = ref({});

 onMounted(async () => {
     //TODO(pjm): first check db for results
     const r = await requestSender.sendRequest("cortexSimRunner", {
         materialId: props.materialId,
     });
     await appState.loadModels(r.simulationId);
     isLoaded.value = true;
 });

 onUnmounted(() => {
     isLoaded.value = false;
     appState.clearModels();
 });

 watch(() => sim.value.reports, () => {
     let i = 0;
     if (sim.value.reports) {
         for (const r of sim.value.reports) {
             r.viewName = r.modelName;
             r.modelName = `${r.modelName}${i++}`;
             appState.models[r.modelName] = {
                 stat: r.stat,
             };
         }
     }
 });

</script>
