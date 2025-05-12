<template>
  <h1>Communication test page</h1>
  <input ref="file" type="file">
  <button class="btn btn-primary" type="button" @click="test">Test</button>
</template>

<script setup>
 import { appState } from '@/services/appstate.js';
 import { msgRouter } from '@/services/msgrouter.js';
 import { requestSender } from '@/services/requestsender.js';
 import { ref } from "vue";

 const srlog = console.log;
 const file = ref(null);

 const fetchWithJSON = async (url, body) => {
     const r = await fetch(url, {
         method: 'POST',
         headers: {
             'Content-Type': 'application/json',
         },
         body: JSON.stringify(body),
     });
     return await checkHTTPResponse(r);
  };

 const websocket = async (url, body) => {
     const r = await msgRouter.send('/simulation-list', { simulationType: 'myapp' }, {});
     if (! r && r.status === '200') {
         throw new Error('websocket request failed:', r);
     }
     return r.data;
 };

 const checkHTTPResponse = async (response) => {
     if (! response.ok) {
         throw new Error('request failed:', response);
     }
     if (response.headers.get('content-type').includes('json')) {
         return await response.json();
     }
     return await response.text();
 };

 const test = async () => {
     testSimpleRequest();
     testLoadModelsFromSimulationList();
     testUploadLibFile();
 };

 const testLoadModelsFromSimulationList = () => {
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
                        }
                        else {
                            throw new Error('Missing models in response:', response);
                        }
                    },
                    {
                        simulation_id: data[0].simulationId,
                        simulation_type: appState.simulationType,
                    },
                    (err) => {
                        throw new Error(err);
                    },
                );
            }
            else {
                throw new Error('listSimulations returned no data');
            }
        },
        {
            simulationType: appState.simulationType,
        }
    );
 };

 const testSimpleRequest = async () => {
     try {
         const r1 = await fetchWithJSON('/simulation-list', { simulationType: appState.simulationType });
         srlog('json fetch simulations:', r1);
         const r2 = await websocket('/simulation-list', { simulationType: appState.simulationType });
         srlog('websocket simulations:', r2);
     }
     catch(error) {
         throw new Error(error);
     }
 };

 const testUploadLibFile = async () => {
     // "/upload-lib-file/<simulation_type>/<simulation_id>/<file_type>"
     if (! file.value.files.length) {
         throw new Error('No file selected');
     }
     const fd = new FormData();
     fd.append('file', file.value.files[0])
     fd.append('simulation_type', appState.simulationType);
     fd.append('simulation_id', appState.models.simulation.simulationId);
     fd.append('file_type', 'dog-testFile');
     const r1 = await msgRouter.send(
         appState.schema.route.uploadLibFile,
         fd,
         {
             transformRequest: (v) => v,
             headers: {
                 'Content-Type': undefined,
             }
         },
     );
     console.log('file upload result:', r1);
 };
</script>
