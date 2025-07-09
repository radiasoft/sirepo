<template>
    <div
        v-if="showRegistration"
        class="row"
    >
        <div class="col-sm-11 col-md-9">
            <div class="row">
                <div class="col-sm-7 offset-sm-5">
                    <p>Please enter your full name to complete your Sirepo registration.</p>
                    <VForm viewName="completeRegistration" fieldDef="basic" v-bind:wantButtons="false">
                        <div class="col-sm-7 offset-sm-5">
                            <p><button
                                   class="btn btn-primary sr-button-save-cancel"
                                   v-bind:disabled="! canSubmit()"
                                   v-on:click="submitForm"
                               >
                                Submit
                            </button></p>
                        </div>
                    </VForm>
                </div>
            </div>
        </div>
    </div>
    <div
        v-else
        class="row text-center"
    >
        <p>Please click the button below to complete the login process.</p>
        <p>
            <button class="btn btn-primary" type="button" v-on:click="submitConfirm">Confirm</button>
        </p>
    </div>
    <VConfirmationModal ref="responseSubmitted" title="Thank you for your request" v-bind:canDismiss="false">
        <p>Your response has been submitted. You will received an email from Sirepo support
            after your request has been reviewed.</p>
    </VConfirmationModal>
</template>

<script setup>
 import VConfirmationModal from '@/components/VConfirmationModal.vue';
 import VForm from '@/components/VForm.vue';
 import { appResources } from '@/services/appresources.js';
 import { appState } from '@/services/appstate.js';
 import { authState } from '@/services/authstate.js';
 import { ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { useRoute } from 'vue-router';

 let ui_ctx;
 const showRegistration = ref(false);
 const responseSubmitted = ref(null);
 const route = useRoute();

 const canSubmit = () => {
     if (! ui_ctx.fields.fullName.val) {
         return false;
     }
     if (authState.isModerated && ! ui_ctx.fields.reason.val) {
         return false;
     }
     return true;
 };

 const submitConfirm = async () => {
     authState.handleLogin(
         await requestSender.sendRequest(
             'authEmailAuthorized',
             {
                 token: route.params.token,
             },
         ),
     );
 };

 const submitForm = async () => {
     const r = await requestSender.sendRequest(
         route.params.token
             ? 'authEmailAuthorized'
             : 'authCompleteRegistration',
         {
             displayName: ui_ctx.fields.fullName.val,
             reason: ui_ctx.fields.reason.val,
             token: route.params.token,
         },
     );
     if (r.state === 'ok' && showRegistration.value && authState.isModerated) {
         responseSubmitted.value.showModal();
         return;
     }
     authState.handleLogin(r);
 };

 appState.clearModels({
     completeRegistration: {},
 });
 appResources.registerViewLogic('completeRegistration', (ctx) => {
     ui_ctx = ctx;
     ui_ctx.fields.fullName.cols = 7;
     ui_ctx.fields.reason.visible = authState.isModerated;
 });

 if (authState.checkNeedCompleteRegistration()) {
     showRegistration.value = parseInt(route.params.needCompleteRegistration)
         || authState.needCompleteRegistration;
 }
</script>
