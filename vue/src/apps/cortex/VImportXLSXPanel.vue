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
    <!--VConfirmationModal
        ref="confirmModal"
        title="Verify Material"
        okText="Save"
        cancelText="Discard"
        v-on:okClicked="confirmMaterial"
        v-on:modalClosed="modalClosed"
    >
        TODO: Show imported material info here
    </VConfirmationModal-->
    <VConfirmationModal
        ref="errorsModal"
        title="Import Errors"
        cancelText="Close"
        size="lg"
    >
        <div v-for="err in errorList" :key="err.line">
            <div class="lead" v-if="err.sheet">{{ err.sheet }} Sheet</div>
            <div>
                <span v-if="err.row">
                    row {{ err.row }}<span v-if="err.col">, col {{ err.col }}</span>:
                </span>
                <span v-if="err.value">{{ err.value }}:</span>
                {{ err.msg }}
            </div>
        </div>
    </VConfirmationModal>
</template>

<script setup>
 import VConfirmationModal from '@/components/VConfirmationModal.vue';
 import VFileUploadButton from '@/apps/cortex/VFileUploadButton.vue';
 import VProgress from '@/components/VProgress.vue';
 import { appState } from '@/services/appstate.js';
 import { ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { uri } from '@/services/uri.js';
 import { useFileDrop } from '@/apps/cortex/useFileDrop.js';

 const confirmModal = ref(null);
 const dropPanel = ref(null);
 const errorList = ref(null);
 const errorsModal = ref(null);
 const isLoaded = appState.isLoadedRef;
 const isProcessing = ref(false);
 const percentComplete = ref(0);
 let file = null;

 const xlsxMimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

 const confirmMaterial = async () => {
     appState.models.simulation.isConfirmed = '1';
     await appState.saveChanges('simulation');
     confirmModal.value.closeModal();
 };

 const templateURL = uri.format('downloadLibFile', {
     simulation_type: appState.simulationType,
     filename: `neutronics_input.xlsx`,
 });

 const modalClosed = async () => {
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

 const parseErrors = (errorMessage) => {
     const p = {
         col: /\scol=(\d+)/,
         row: /\srow=(\d+)/,
         sheet: /\ssheet=(.*)/,
         value: /(invalid\s.*?=\w*\s)/,
     };
     const res = [];
     let sheet = undefined;
     for (let line of errorMessage.split("\n")) {
         const e = {
             line: line,
         };
         for (const f in p) {
             const m = line.match(p[f]);
             if (m) {
                 e[f] = m[1];
                 line = line.replace(p[f], '');
             }
         }
         if (line) {
             e.msg = line;
             if (e.value) {
                 e.value = e.value.trim().replace(/=$/, '');
             }
             if (e.sheet && e.sheet === sheet) {
                 delete e.sheet;
             }
             else {
                 sheet = e.sheet;
             }
             res.push(e);
         }
     }
     return res;
 };

 const startProcessing = async () => {
     isProcessing.value = true;
     const importFile = async () => {
         const r = await requestSender.importFile(
             file,
             appState.formatFileType("materialImport", "xlsxFile"),
         );
         isProcessing.value = false;
         file = null;
         if (r.data.error) {
             errorList.value = parseErrors(r.data.error);
             errorsModal.value.showModal();
             return;
         }
         // confirmModal.value.showModal();
         await appState.saveChanges('materialImport');
     }
     await importFile();
 };

 const { isOverDropZone, isInvalidMimeType } = useFileDrop(dropPanel, onDrop, xlsxMimeType);

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
