<template>
  <h1>Communication test page</h1>
  <input ref="file" type="file">
  <button class="btn btn-primary" type="button" @click="test">Test</button>
</template>

<script setup>
 import { appState } from '@/services/appstate.js';
 import { msgRouter } from '@/services/msgrouter.js';
 import { requestSender } from '@/services/requestsender.js';
 import { onUnmounted, ref } from "vue";

 const srlog = console.log;
 const file = ref(null);

 const test = async () => {
     await testLoadModelsFromSimulationList();
     await testUploadLibFile();
     srlog('test done');
 };

 const srExceptionHandler = (srException, errorCallback) => {
     srlog('got a srException callback:', srException);
 };

 const testLoadModelsFromSimulationList = () => {
     //TODO(pjm): consider giving requestSender.sendRequest a Promise interface like msgRouter
     const d = {};
     const p = new Promise((resolve, reject) => {
         Object.assign(d, {resolve, reject });
     });
     requestSender.sendRequest(
         'listSimulations',
         (data) => {
             if (data.length > 0) {
                 // test loading the first sim in the lsit
                 requestSender.sendRequest(
                     'simulationData',
                     (response) => {
                         if (response.models) {
                             appState.loadModels(response.models);
                             srlog('loaded models:', response.models);
                             d.resolve();
                         }
                         else {
                             d.reject();
                             throw new Error('Missing models in response:', response);
                         }
                     },
                     {
                         simulation_id: data[0].simulationId,
                     },
                     (err) => {
                         d.reject();
                         throw new Error(err);
                     },
                 );
             }
             else {
                 d.reject();
                 throw new Error('listSimulations returned no data');
             }
         },
         {},
     );
     return p;
 };

 const testUploadLibFile = async () => {
     // "/upload-lib-file/<simulation_type>/<simulation_id>/<file_type>"
     if (! file.value.files.length) {
         throw new Error('No file selected');
     }

     const formData = (values) => {
         const fd = new FormData();
         for (const [k, v] of Object.entries(values)) {
             fd.append(k, v);
         }
         return fd;
     };

     srlog('using sim_id:', appState.models.simulation.simulationId);
     const r1 = await msgRouter.send(
         appState.schema.route.uploadLibFile,
         formData({
             file: file.value.files[0],
             file_type: 'dog-testFile',
             simulation_id: appState.models.simulation.simulationId,
             simulation_type: appState.simulationType,
         }),
     );
     srlog('file upload result:', r1);
 };

 requestSender.registerSRExceptionHandler(srExceptionHandler);

 onUnmounted(() => {
     requestSender.unregisterSRExceptionHandler(srExceptionHandler);
 });

</script>
