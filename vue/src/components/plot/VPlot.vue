<template>
    <div v-bind:class="{
        'sr-panel-loading': qItem,
        'sr-panel-error': false,
    }">
        <div v-if="qItem"
             class="lead sr-panel-wait"><span class="bi bi-hourglass"></span>
            Requesting Data
        </div>
    </div>
    <VLine v-bind:data="data"></VLine>
</template>

<script setup>
 //TODO(pjm): support multiple plot types, Line, HeatMap, 3D, etc.
 import VLine from '@/components/plot/VLine.vue';
 import { appState } from '@/services/appstate.js';
 import { ref, onMounted, onUnmounted } from 'vue';
 import { simQueue } from '@/services/simqueue.js';
 import { useModelSaved } from '@/components/useModelSaved.js';

 const props = defineProps({
     modelName: String,
 });

 const data = ref(null);
 const qItem = ref(null);

 const cancelItem = () => {
     if (qItem.value) {
         simQueue.cancelItem(qItem.value);
         qItem.value = null;
     }
 };

 const load = () => {
     qItem.value = simQueue.addTransientItem(
         props.modelName,
         appState.models,
         responseHandler,
     );
 };

 const responseHandler = (resp) => {
     qItem.value = null;
     if (resp.error) {
         //TODO(pjm): show error message over plot
     }
     else {
         data.value = () => resp;
     }
 };

 useModelSaved((names) => {
     cancelItem();
     load();
 });

 onMounted(() => {
     load();
 });

 onUnmounted(() => {
     cancelItem();
 });
</script>
