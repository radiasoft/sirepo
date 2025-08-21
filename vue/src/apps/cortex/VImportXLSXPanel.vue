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
            <VProgress v-bind:percentComplete="0" />
        </div>
    </div>
    <VConfirmationModal
        ref="confirmModal"
        title="Material Imported"
        cancelText="Close"
    >
        Imported <strong>{{ materialName }}</strong> successfully
    </VConfirmationModal>
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
 import { db } from '@/apps/cortex/db.js';
 import { ref } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { schema } from '@/services/schema.js';
 import { uri } from '@/services/uri.js';
 import { useFileDrop } from '@/apps/cortex/useFileDrop.js';

 const confirmModal = ref(null);
 const dropPanel = ref(null);
 const errorList = ref(null);
 const errorsModal = ref(null);
 const isProcessing = ref(false);
 const materialName = ref('');
 const xlsxMimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

 const templateURL = uri.format('downloadLibFile', {
     simulation_type: schema.simulationType,
     filename: 'materials_input.xlsx',
 });

 const onDrop = (files) => {
     if (! isProcessing.value) {
         processFile(files[0]);
     }
 };

 const processFile = async (file) => {
     isProcessing.value = true;
     const r = await requestSender.importFile(file);
     isProcessing.value = false;
     if (r.data.error) {
         errorList.value = r.data.error;
         errorsModal.value.showModal();
         return;
     }
     materialName.value = r.data.models.parsed_material[0].material_name;
     confirmModal.value.showModal();
     db.updated();
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
