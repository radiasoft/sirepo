<template>
    <div class="card card-body bg-light sr-drop-zone"
         v-bind:class="{
             'sr-drag-over': isOverDropZone || isProcessing,
             'sr-invalid': isInvalidMimeType,
         }"
         ref=dropPanel
    >
        <p>Drag and drop an Excel material file here to process a new material.</p>
        <p>
            <strong>
                <a v-bind:href="templateURL">
                    Use this Excel template
                    <span class="bi bi-cloud-download"></span>
                </a>
            </strong>
            for reference.
        </p>
        <div class="text-end" v-if="! isProcessing">
            <VFileUploadButton
                v-on:fileChanged="onDrop"
                v-bind:mimeType="xlsxMimeType"
            >
                Upload Material Spreadsheet
            </VFileUploadButton>
        </div>
        <div v-if="isProcessing">
            Processing, please wait...
            <VProgress v-bind:percentComplete="percentComplete" />
        </div>
    </div>
    <VConfirmationModal
        ref="confirm"
        title="Verify Material"
        okText="Save"
        cancelText="Discard"
        v-on:okClicked="confirmMaterial"
        v-on:modalClosed="modalClosed"
    >
        TODO: Show imported material info here
    </VConfirmationModal>
</template>

<script setup>
 import VConfirmationModal from '@/components/VConfirmationModal.vue';
 import VFileUploadButton from '@/apps/cortex/VFileUploadButton.vue';
 import VProgress from '@/components/VProgress.vue';
 import { appState } from '@/services/appstate.js';
 import { ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { simQueue } from '@/services/simqueue.js';
 import { uri } from '@/services/uri.js';
 import { useFileDrop } from '@/apps/cortex/useFileDrop.js';

 const confirm = ref(null);
 const dropPanel = ref(null);
 const isLoaded = appState.isLoadedRef;
 const isProcessing = ref(false);
 const percentComplete = ref(0);
 let file = null;

 const xlsxMimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

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
     filename: `${appState.formatFileType('materialImport', 'xlsxFile')}.neutronics_input.xlsx`,
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

 const startProcessing = async () => {
     isProcessing.value = true;
     return;
     // redirect to simulation url, isLoaded will activate below
     uri.localRedirect(
         'importXLSX',
         {
             simulationId: r.models.simulation.simulationId,
         },
     );
 };

 const { isOverDropZone, isInvalidMimeType } = useFileDrop(dropPanel, onDrop, xlsxMimeType);

 watch(isLoaded, async () => {
     if (! isLoaded.value || ! file) {
         return;
     }

     const importFile = async () => {
         const r = await requestSender.importFile(
             file,
             appState.formatFileType("materialImport", "xlsxFile"),
         );
         file = null;
         if (r.data.error) {
             //TODO(pjm): display the error
             console.log('has error in response:\n', r.data.error);
             clearAndRedirectHome();
             return;
         }
         await appState.saveChanges('materialImport');
     }

     await importFile();
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
