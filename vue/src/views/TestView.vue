<template>
  <h1>Communication test page</h1>
  <button class="btn btn-primary" type="button" @click="test">Test</button>
</template>

<script setup>

 import { msgRouter } from '@/services/msgrouter.js';

 const fetchGET = async (url, body) => {
     return await fetchWithJSON(url);
 };

 const fetchWithJSON = async (url, body) => {
     return await fetch(url, {
         method: body ? 'POST' : 'GET',
         headers: {
             'Content-Type': 'application/json',
         },
         body: body ? JSON.stringify(body) : null,
     });
  };

 const fetchWithFormData = async (url, body) => {
     const formData = new URLSearchParams();
     for (const k in body)  {
         formData.append(k, body[k]);
     }
     return await fetch(url, {
         method: body ? 'POST' : 'GET',
         headers: {
             'Content-Type': 'application/x-www-form-urlencoded',
         },
         body: formData.toString(),
     });
 };

 const checkResponse = async (response) => {
     if (! response.ok) {
         console.log('request failed:', response);
     }
     else {
         if (response.headers.get('content-type').includes('json')) {
             const json = await response.json();
             console.log('got json response:', json);
             return json;
         }
         else {
             const text = await response.text();
             console.log('got non-json response:', text);
             return text;
         }
     }
 };

 const addScriptTag = async (url) => {
     const t = document.createElement('script');
     document.body.appendChild(Object.assign(t, {
         src: url,
         type: 'text/javascript',
         async: true,
     }));
     return new Promise((resolve, reject) => t.onload = resolve);
 };

 const test = async () => {
     //const response = await fetchWithJSON('/simulation-schema', { simulationType: 'myapp' });
     let response = await fetchWithFormData('/simulation-schema', { simulationType: 'myapp' });
     SIREPO.APP_SCHEMA = await checkResponse(response);
     await addScriptTag('/auth-state');
     console.log(SIREPO);
     response = await fetchWithJSON('/simulation-list', { simulationType: 'myapp' });
     checkResponse(response);
     response = await msgRouter.send('/simulation-list', { simulationType: 'myapp' }, {});
     console.log('msgRouter response:', response);
 };
</script>
