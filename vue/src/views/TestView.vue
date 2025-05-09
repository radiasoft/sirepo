<template>
  <h1>Communication test page</h1>
  <button class="btn btn-primary" type="button" @click="test">Test</button>
</template>

<script setup>
 import { appState } from '@/services/appstate.js';
 import { msgRouter } from '@/services/msgrouter.js';

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
     const r1 = await fetchWithJSON('/simulation-list', { simulationType: appState.simulationType });
     console.log('json fetch simulations:', r1);
     const r2 = await websocket('/simulation-list', { simulationType: appState.simulationType });
     console.log('websocket simulations:', r2);
 };
</script>
