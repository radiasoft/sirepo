<template>
    <div class="mb-3">Simulation state: {{ state }}{{ statusDots }}</div>
    <div v-if="! isBusy()">
      <button v-on:click="startSim">Start New Simulation</button>
    </div>
    <div v-if="isRunning()">
      <button v-on:click="cancelSim">End Simulation</button>
    </div>
</template>

<script setup>
 import { appState } from '@/services/appstate.js';
 import { ref, onMounted, onUnmounted } from 'vue';
 import { simQueue } from '@/services/simqueue.js';

 const props = defineProps({
     sim: Object,
     viewName: String,
 });

 const state = ref("unknown"); // unknown or sim state
 const statusDots = ref("");
 let qItem = null;

 //TODO(pjm): unknown + isRunning
 const isBusy = () => ["unknown", "pending", "queued", "running"].includes(state.value);

 const isRunning = () => ["pending", "queued", "running"].includes(state.value);

 const cancelSim = () => {
     simQueue.cancelItem(qItem);
     state.value = "canceled";
     qItem = null;
 };

 const simStatusHandler = (data) => {
     //TODO(pjm): display and update elapsed time and percent complete
     //TODO(pjm): display errors
     if (data.state !== "missing" && data.queueState) {
         state.value = data.queueState;
     }
     else if (data.state) {
         if (state.value != data.state) {
             state.value = data.state;
             statusDots.value = '';
         }
     }
     if (isRunning()) {
         if (! statusDots.value || statusDots.value.length >= 3) {
             statusDots.value = '.';
         }
         else {
             statusDots.value += '.';
         }
     }
     else {
         statusDots.value = '';
         qItem = null;
     }
     if (data.reports) {
         for (let f in data) {
             props.sim[f] = data[f];
         }
     }
 };

 const startSim = () => {
     if (qItem) {
         return;
     }
     //TODO(pjm): clear all sim state
     props.sim.reports = [];
     state.value = "pending";
     qItem = simQueue.addPersistentItem(
         props.viewName,
         appState.models,
         simStatusHandler,
     );
 };

 onMounted(() => {
     simQueue.addPersistentStatusItem(
         props.viewName,
         appState.models,
         simStatusHandler,
     );
 });
</script>
