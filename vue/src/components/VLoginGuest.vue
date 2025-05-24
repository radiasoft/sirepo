<template>
    <div class="row">
        <div class="col-sm-6 offset-sm-3">
            <div ng-switch-default class="card card-body bg-light text-center">{{ message }}</div>
        </div>
    </div>
</template>

<script setup>
 import { appState } from '@/services/appstate.js';
 import { authState } from '@/services/authstate.js';
 import { requestSender } from '@/services/requestsender.js';
 import { useRouter } from 'vue-router';

 const router = useRouter();
 let message = 'Creating your account. Please wait...';
 requestSender.sendRequest(
     'authGuestLogin',
     (response) => {
         if (response.authState) {
             authState.init(response.authState);
             //TODO(pjm): root uri
             router.replace('/' + appState.simulationType);
         }
     },
     {
         simulation_type: appState.simulationType,
     },
 );

</script>
