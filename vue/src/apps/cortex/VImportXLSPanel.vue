<template>
    <div class="card card-body bg-light sr-drop-zone"
         :class="{
             'sr-drag-over': isOverDropZone || isProcessing,
             'sr-invalid': isInvalidMimeType,
         }"
         ref=dropPanel
    >
        <p>Drag and drop an XLSX material file here to process a new material.</p>
        <p>
            Use this
            <strong>
                <a :href="templateURL">
                    template XLSX
                    <span class="bi bi-cloud-download"></span>
                </a>
            </strong>
            for reference.
        </p>
        <div class="text-end" v-if="! isProcessing">
            <label for="dropZoneFile" class="btn btn-outline-secondary">Upload Material XLSX</label>
            <input
                style="display: none"
                id="dropZoneFile"
                type="file"
                @change="onFileChanged"
                :accept="xlsMimeType"
                ref="fileInput"
            />
        </div>
        <div v-if="isProcessing">
            Processing, please wait...
            <VProgress :percentComplete="percentComplete" />
        </div>
    </div>
    <VConfirmationModal
        ref="confirm"
        title="Verify Material"
        okText="Save"
        cancelText="Discard"
        @okClicked="confirmMaterial"
        @modalClosed="modalClosed"
    >
        TODO: Show imported material info here
    </VConfirmationModal>
</template>

<script setup>
 import { appState } from '@/services/appstate.js';
 import { ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { simQueue } from '@/services/simqueue.js';
 import { uri } from '@/services/uri.js';
 import { useFileDrop } from '@/apps/cortex/useFileDrop.js';
 import VProgress from '@/components/VProgress.vue';
 import VConfirmationModal from '@/components/VConfirmationModal.vue';

 const confirm = ref(null);
 const dropPanel = ref(null);
 const isLoaded = appState.isLoadedRef;
 const isProcessing = ref(false);
 const percentComplete = ref(0);
 let fileInput = ref(null);
 let file = null;

 const xlsMimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

 const clearAndRedirectHome = () => {
     isProcessing.value = false;
     appState.clearModels();
     uri.redirectAppRoot();
 };

 const confirmMaterial = async () => {
     appState.models.simulation.isConfirmed = '1';
     await appState.saveChanges('simulation');
     confirm.value.closeModal();
 };

 const templateURL = uri.format('downloadLibFile', {
     simulation_type: appState.simulationType,
     filename: `${appState.formatFileType('materialImport', 'xlsFile')}.neutronics_input.xlsx`,
 });

 const modalClosed = async () => {
     clearAndRedirectHome();
     if (appState.models.simulation.isConfirmed === '0') {
         await appState.deleteSimulation(appState.models.simulation.simulationId);
     }
 }

 const onDrop = (files) => {
     if (! isProcessing.value) {
         file = files[0];
         startProcessing();
     }
 };

 const onFileChanged = () => {
     if (fileInput.value && fileInput.value.files.length) {
         file = fileInput.value.files[0];
         startProcessing();
     }
 };

 const startProcessing = async () => {
     isProcessing.value = true;
     // create new sim
     const r = await requestSender.sendRequest(
         'newSimulation',
         appState.setModelDefaults({
             name: 'imported material',
         }, 'simulation'),
     );
     // redirect to simulation url, isLoaded will activate below
     uri.localRedirect(
         'importXLS',
         {
             simulationId: r.models.simulation.simulationId,
         },
     );
 };

 const { isOverDropZone, isInvalidMimeType } = useFileDrop(dropPanel, onDrop, xlsMimeType);

 watch(isLoaded, async () => {
     if (! isLoaded.value || ! file) {
         return;
     }

     const addLibFile = async () => {
         const r = await requestSender.uploadLibFile(
             file,
             appState.formatFileType("materialImport", "xlsFile"),
             // confirm - overwrite if exists
             true,
         );
         file = null;
         if (r.data.error) {
             //TODO(pjm): display the error
             console.log('has error in response:', r.data.error);
             clearAndRedirectHome();
             return;
         }
         appState.models.materialImport.xlsFile = r.data.filename;
         await appState.saveChanges('materialImport');
     }

     const runSimulation = () => {
         const simComputeModel = 'materialImport';
         simQueue.addPersistentItem(
             simComputeModel,
             appState.models,
             (resp) => {
                 console.log('got sim response:', resp);
                 if (resp.state === 'error') {
                     //TODO(pjm): display error in banner
                     clearAndRedirectHome();
                     return;
                 }
                 if (resp.state === 'completed') {
                     isProcessing.value = false;
                     confirm.value.showModal();
                     return;
                 }
             },
         );
     }

     await addLibFile();
     runSimulation();
 });
</script>

<style scoped>
 .sr-drop-zone {
     border: 2px dashed #ccc;
 }
 .sr-drop-zone.sr-drag-over {
     border: 2px solid var(--bs-primary);
 }
 .sr-drop-zone.sr-drag-over.sr-invalid {
     border: 2px solid var(--bs-danger);
     cursor: not-allowed;
 }
</style>
