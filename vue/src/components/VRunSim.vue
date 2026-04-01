<template>
    <div v-if="showState()">Simulation state: {{ state }}{{ statusDots }}</div>
    <div v-if="elapsedTime && state !== 'canceled'">Elapsed time: {{ elapsedTime }}</div>
    <div v-if="isRunning()">
      <div class="progress mt-3" role="progressbar">
          <div class="progress-bar progress-bar-striped" v-bind:style="{ width: percentComplete + '%' }"></div>
      </div>
      <button
          type="button"
          class="btn btn-outline-primary mt-3"
          v-on:click="cancelSim">End Simulation
      </button>
    </div>
    <div v-if="! isBusy()">
      <button
          type="button"
          class="btn btn-outline-primary mt-3"
          v-on:click="startSim">Start New Simulation
      </button>
    </div>
</template>

<script setup>
 import { appState } from '@/services/appstate.js';
 import { ref, onMounted, onUnmounted, watch } from 'vue';
 import { simQueue } from '@/services/simqueue.js';
 import { util } from '@/services/util.js';

 const props = defineProps({
     sim: Object,
     viewName: String,
 });

 const state = ref("unknown"); // unknown or sim state
 const statusDots = ref("");
 const percentComplete = ref(0);
 const elapsedTime = ref(0);
 let qItem = null;

 //TODO(pjm): unknown + isRunning
 const isBusy = () => ["unknown", "pending", "queued", "running"].includes(state.value);

 const isRunning = () => ["pending", "queued", "running"].includes(state.value);

 const cancelSim = () => {
     if (qItem) {
         simQueue.cancelItem(qItem);
     }
     state.value = "canceled";
     statusDots.value = '';
     qItem = null;
 };

 const showState = () => ! ["missing", "unknown"].includes(state.value);

 const simStatusHandler = (data) => {
     percentComplete.value = parseInt(data.percentComplete || 2);
     elapsedTime.value = data.elapsedTime ? util.formatTime(data.elapsedTime) : 0;

     //TODO(pjm): display errors
     if (data.state !== "missing" && data.state !== "canceled" && data.queueState) {
         state.value = data.queueState;
     }
     else if (data.state) {
         if (state.value !== data.state) {
             state.value = data.state;
             statusDots.value = '';
         }
     }
     if (isBusy()) {
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
     elapsedTime.value = 0
     state.value = "pending";
     qItem = simQueue.addPersistentItem(
         props.viewName,
         appState.models,
         simStatusHandler,
     );
 };

 onMounted(() => {
     qItem = simQueue.addPersistentStatusItem(
         props.viewName,
         appState.models,
         simStatusHandler,
     );
 });

 onUnmounted(() => {
     if (qItem) {
         simQueue.removeItem(qItem);
     }
 });

 watch(() => props.viewName, () => {
     if (qItem) {
         simQueue.removeItem(qItem);
     }
     qItem = simQueue.addPersistentStatusItem(
         props.viewName,
         appState.models,
         simStatusHandler,
     );
 });

</script>
