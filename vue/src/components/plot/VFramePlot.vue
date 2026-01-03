<template>
    <div v-bind:class="{
        'sr-panel-loading': isLoading,
        'sr-panel-error': errorMessage,
    }">
        <div v-if="isLoading"
             class="lead sr-panel-wait"><span class="bi bi-hourglass"></span>
            Requesting Data
        </div>
        <div v-if="errorMessage"
             class="lead sr-panel-wait">
            An error occurred loading the data:
            <div>{{ errorMessage }}</div>
        </div>
    </div>
    <VLine v-bind:data="data"></VLine>
    <VFrameNav
        v-bind:frameCount="frameCount"
        v-on:frameChanged="onFrameChanged"
        v-on:isPlayingChanged="onIsPlayingChanged"
    ></VFrameNav>
</template>

<script setup>
 //TODO(pjm): share with VPlot
 import VFrameNav from '@/components/plot/VFrameNav.vue';
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

 const errorMessage = ref("");
 const isLoading = ref(false);
 const data = ref(null);
 const frameCount = ref(1);
 let frameIndex = 1;
 let isPlaying = false;

 const frameId = (frameReport) => {
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
     const i = frameIndex;
     const id = frameId(props.viewName);
     errorMessage.value = "";
     objectStore.getFrame(id, props.viewName, async (resp) => {
         if (resp) {
             data.value = () => resp;
             return;
         }
         if (isLoading.value) {
             // already running a request
             return;
         }
         isLoading.value = true;
         resp = await requestSender.sendRequest('simulationFrame', {
             frame_id: id,
         });
         isLoading.value = false;
         if (resp.error) {
             errorMessage.value = resp.error;
         }
         else {
             objectStore.saveFrame(id, props.viewName, resp);
             if (i == frameIndex) {
                 data.value = () => resp;
             }
             else {
                 // the requested frame has changed during the request, load new data
                 setTimeout(() => load(), 0);
             }
         }
     });
 };

 const onFrameChanged = (newFrameIndex) => {
     if (newFrameIndex !== frameIndex) {
         frameIndex = newFrameIndex;
         load();
     }
 };

 const onIsPlayingChanged = (newIsPlaying) => {
     if (newIsPlaying !== isPlaying) {
         isPlaying = newIsPlaying;
     }
 };

 onMounted(() => {
     const getFrameCount = () => {
         for (let r of props.sim.reports) {
             if (r.modelName == props.viewName) {
                 return r.frameCount;
             }
         }
         return props.sim.frameCount;
     };
     frameCount.value = getFrameCount();
     load();
 });

 onUnmounted(() => {
     isLoading.value = false;
 });
</script>
