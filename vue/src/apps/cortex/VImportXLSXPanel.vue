<template>
    <div class="card card-body bg-light sr-drop-zone"
         v-bind:class="{
             'sr-drag-over': isOverDropZone || isProcessing,
             'sr-invalid': isInvalidMimeType,
         }"
         ref=dropPanel
    >
        <p>Drag and drop an Excel material file here to import one or many materials.</p>
        <p>
            <strong>
                <a v-bind:href="templateURL">
                    Single material Excel template
                    <span class="bi bi-cloud-download"></span>
                </a>
            </strong>
        </p>
        <p>
            <strong>
                <a v-bind:href="multiTemplateURL">
                    Multiple materials Excel template
                    <span class="bi bi-cloud-download"></span>
                </a>
            </strong>
            with one row per material.
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
        <span v-if="materialCount > 1">
            Imported <strong>{{ materialCount }}</strong> materials successfully.
            Simulation of <strong>{{ materialName }}</strong> has started.
        </span>
        <span v-else>
            Imported <strong>{{ materialName }}</strong> successfully
        </span>
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
                <span v-if="err.value">{{ err.value }}</span>
                <span v-if="err.value && err.msg">:</span>
                {{ err.msg }}
            </div>
        </div>
        <div v-if="moreErrors > 0">and {{ moreErrors }} more</div>
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
 const maxErrors = 50;
 const moreErrors = ref(0);
 const materialCount = ref(0);
 const materialName = ref('');
 const xlsxMimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

 const templateURL = uri.format('downloadLibFile', {
     simulation_type: schema.simulationType,
     filename: 'materials_input.xlsx',
 });

 const multiTemplateURL = uri.format('downloadLibFile', {
     simulation_type: schema.simulationType,
     filename: 'materials_multi_input.xlsx',
 });

 const onDrop = (files) => {
     if (! isProcessing.value) {
         processFile(files[0]);
     }
 };

 const processFile = async (file) => {
     const filterSheets = (errorList) => {
         let s = null;
         for (const e of errorList) {
             if (! e.sheet) {
                 continue;
             }
             if (e.sheet === s) {
                 e.sheet = null;
             }
             else {
                 s = e.sheet;
             }
         }
         return errorList;
     };

     const showErrors = (errors) => {
         // many materials can have many errors
         errorList.value = filterSheets(errors).slice(0, maxErrors);
         moreErrors.value = errors.length - errorList.value.length;
         errorsModal.value.showModal();
     };

     isProcessing.value = true;
     let r;
     try {
         r = await db.insertMaterial(file);
     }
     catch (e) {
         // e.g. the server could not be reached
         showErrors([{ msg: 'Unable to import the file, please try again' }]);
         return;
     }
     finally {
         isProcessing.value = false;
     }
     if (r.error) {
         // parse and db errors are a list, an internal error is a single value
         showErrors(Array.isArray(r.error) ? r.error : [{ msg: r.error.value }]);
         return;
     }
     materialCount.value = r.op_result.materials.length;
     materialName.value = r.op_result.material_name;
     confirmModal.value.showModal();
     db.updated();
     // do not await simulation completion
     requestSender.sendRequest("cortexSim", {
         op_name: 'runSim',
         op_args: {
             report: "hcpbSlabAnimation",
             material_id: r.op_result.material_id,
         },
     });
 };

 const { isOverDropZone, isInvalidMimeType } = useFileDrop(dropPanel, onDrop, xlsxMimeType);

</script>

<style scoped>
 .sr-drop-zone {
     border: 2px dashed #ccc;
     min-height: 270px;
     display: flex;
     justify-content: center;
 }
 .sr-drop-zone.sr-drag-over {
     border: 2px solid var(--bs-primary);
 }
 .sr-drop-zone.sr-drag-over.sr-invalid {
     border: 2px solid var(--bs-danger);
     cursor: not-allowed;
 }
</style>
