<template>
    <div v-if="isLoaded">
        <VRunSim v-bind:sim="sim" v-bind:viewName="neutronics"></VRunSim>
    </div>
</template>

<script setup>
 import VRunSim from '@/components/VRunSim.vue';
 import { appState } from '@/services/appstate.js';
 import { onMounted, onUnmounted, ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';

 const props = defineProps({
     materialId: String,
     neutronics: String,
 });
 const emit = defineEmits(['simCompleted']);
 const isLoaded = appState.isLoadedRef;
 const sim = ref({});

 onMounted(async () => {
     const r = await requestSender.sendRequest("cortexSim", {
         op_name: 'synchronize',
         op_args: {
             material_id: props.materialId,
         },
     });
     await appState.loadModels(r.simulationId);
 });

 onUnmounted(() => {
     if (isLoaded.value) {
         appState.clearModels();
     }
 });

 watch(() => sim.value.frameCount, async () => {
     if (sim.value.reports) {
         emit('simCompleted');
     }
 });

</script>
