
<template>
    <div class="row text-center">
        <p>Please click the button below to complete the login process.</p>
        <p>
            <button class="btn btn-primary" type="button" @click="confirm">Confirm</button>
        </p>
    </div>
</template>

<script setup>
 import { appState } from '@/services/appstate.js';
 import { authState } from '@/services/authstate.js';
 import { requestSender } from '@/services/requestsender.js';
 import { useRoute, useRouter } from 'vue-router';

 const route = useRoute();
 const router = useRouter();

 const confirm = () => {
    // self.submit = function() {
    //     requestSender.sendRequest(
    //         {
    //             routeName: 'authEmailAuthorized',
    //             '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
    //             '<token>': p.token,
    //         },
    //         function (data) {
    //             if (data.state === 'ok' && self.needCompleteRegistration && authState.isModerated()) {
    //                 $('#sr-complete-registration-done').modal('show');
    //                 return;
    //             }
    //             authState.handleLogin(data, self);
    //         },
    //         {
    //             token: p.token,
    //             displayName: self.data.displayName,
    //             reason: self.data.reason,
    //             simulationType: SIREPO.APP_SCHEMA.simulationType,
    //         }
    //     );
    // };
     requestSender.sendRequest(
         'authEmailAuthorized',
         (response) => {
             if (response.state === 'ok') {
                 if (response.authState) {
                     authState.init(response.authState);
                     //TODO(pjm): root uri
                     router.replace('/' + appState.simulationType);
                 }
                 return;
             }
             //TODO(pjm): show error message here
         },
         {
             simulation_type: route.params.simulationType,
             token: route.params.token,
         },
         //TODO(pjm): use same response handler as success
     );

 };
</script>
