<template>
    <div class="card card-body bg-light drop-zone"
         :class="{ 'drag-over': isOverDropZone }"
         ref=dropPanel
    >
        <p>Drag and drop an XLS material file here to process a new material.</p>
        <p>
            Use this
            <strong>
                <a href>
                    template XLS
                    <span class="bi bi-cloud-download"></span>
                </a>
            </strong>
            for reference.
        </p>
        <div class="text-end">
            <button
                type="button"
                class="btn btn-outline-secondary"
                @click="showUploadModal"
            >
                Upload Material XLS
            </button>
        </div>
    </div>
</template>

<script setup>
 import { appState } from '@/services/appstate.js';
 import { ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { simQueue } from '@/services/simqueue.js';
 import { uri } from '@/services/uri.js';
 import { useFileDrop } from '@/apps/cortex/useFileDrop.js';

 const dropPanel = ref(null);
 const isLoaded = appState.isLoadedRef;

 const onDrop = async (files) => {
     // create new sim
     const r = await requestSender.sendRequest(
         'newSimulation',
         appState.setModelDefaults({
             name: 'pending import',
         }, 'simulation'),
     );
     uri.localRedirect(
         'importXLS',
         {
             simulationId: r.models.simulation.simulationId,
         },
     );
 };

 const { isOverDropZone } = useFileDrop(dropPanel, onDrop);

 const showUploadModal = () => {
 };

 watch(isLoaded, () => {
     if (! isLoaded.value) {
         return;
     }
     // add lib file
     // run simulation
     const simComputeModel = 'animation';
     simQueue.addPersistentItem(
         simComputeModel,
         appState.models,
         (resp) => {
             console.log('got response:', resp);
         },
     );

     // save changes
     // confirm import or delete sim
     // return to search page

 });
</script>

<style scoped>
 .drop-zone {
     border: 2px dashed #ccc;
 }
 .drop-zone.drag-over {
     border: 2px solid var(--bs-primary);
 }
</style>
