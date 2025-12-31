<template>
    <div v-bind:class="{
        'sr-panel-loading': isLoading,
        'sr-panel-error': false,
    }">
        <div v-if="isLoading"
             class="lead sr-panel-wait"><span class="bi bi-hourglass"></span>
            Requesting Data
        </div>
    </div>
    <VLine v-bind:data="data"></VLine>
</template>

<script setup>
 //TODO(pjm): share with VPlot
 import VLine from '@/components/plot/VLine.vue';
 import { appState } from '@/services/appstate.js';
 import { objectStore } from '@/services/objectstore.js';
 import { ref, onMounted, onUnmounted } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { schema } from '@/services/schema.js';

 const props = defineProps({
     viewName: String,
     sim: Object,
 });

 const isLoading = ref(false);

 const data = ref(null);

 const frameId = (frameReport, frameIndex) => {
     const v = [
         // POSIT: same as sirepo.sim_data._FRAME_ID_KEYS
         frameIndex,
         frameReport,
         appState.models.simulation.simulationId,
         schema.simulationType,
         props.sim.computeJobHash,
         props.sim.computeJobSerial,
     ];
     const m = appState.models[frameReport] || appState.models[props.sim.computeModel];
     const f = schema.frameIdFields[frameReport] || schema.frameIdFields[props.sim.computeModel];
     if (! f) {
         throw new Error('frameReport=' + frameReport + ' missing from schema frameIdFields');
     }
     // POSIT: same as sirepo.sim_data._FRAME_ID_SEP
     return v.concat(f.map(a => m[a])).join('*');
 };

 const load = () => {
     //TODO(pjm): track current index
     const index = 1
     const id = frameId(props.viewName, index);
     objectStore.getFrame(id, props.viewName, async (resp) => {
         if (resp) {
             data.value = () => resp;
             return;
         }
         isLoading.value = true;
         resp = await requestSender.sendRequest('simulationFrame', {
             frame_id: id,
         });
         if (isLoading.value) {
             isLoading.value = false;
             //TODO(pjm): check for errors
             objectStore.saveFrame(id, props.viewName, resp);
             //TODO(pjm): only set data.value if load index matches currentIndex
             data.value = () => resp;
         }
     });
 };

 onMounted(() => {
     load();
 });

 onUnmounted(() => {
     isLoading.value = false;
 });
</script>
