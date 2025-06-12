<template>
    <div class="row">
        <div class="col-sm-11 col-md-9">
            <div class="row">
                <div class="col-sm-7 offset-sm-5">
                    <p>Please enter your full name to complete your Sirepo registration.</p>
                    <VForm viewName="completeRegistration" fieldDef="basic" :wantButtons="false">
                        <div class="col-sm-7 offset-sm-5">
                            <p><button
                                   class="btn btn-primary sr-button-save-cancel"
                                   :disabled="! canSubmit()"
                                   @click="submitForm"
                               >
                                Submit
                            </button></p>
                        </div>
                    </VForm>
                </div>
            </div>
        </div>
    </div>
    <VConfirmationModal ref="confirm" title="Thank you for your request" :canDismiss="false">
        <p>Your response has been submitted. You will received an email from Sirepo support
            after your request has been reviewed.</p>
    </VConfirmationModal>
</template>

<script setup>
 import VConfirmationModal from '@/components/VConfirmationModal.vue';
 import VForm from '@/components/VForm.vue';
 import { appState } from '@/services/appstate.js';
 import { authState } from '@/services/authstate.js';
 import { ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';

 let isBusy = false;
 let ui_ctx;
 const confirm = ref(null);

 const canSubmit = () => {
     if (isBusy) {
         return false;
     }
     if (! ui_ctx.fields.fullName.val) {
         return false;
     }
     if (authState.isModerated() && ! ui_ctx.fields.reason.val) {
         return false;
     }
     return true;
 };

 const handleResponse = (response) => {
     if (response.state === 'ok' && authState.needCompleteRegistration && authState.isModerated()) {
         confirm.value.showModal();
         return;
     }
     const err = authState.handleLogin(response);
     if (err) {
         ui_ctx.fields.fullName.val = '';
         ui_ctx.fields.fullName.error = err;
     }
 };

 const submitForm = () => {
     requestSender.sendRequest(
         'authCompleteRegistration',
         handleResponse,
         {
             displayName: ui_ctx.fields.fullName.val,
             reason: ui_ctx.fields.reason.val,
         },
         handleResponse,
     );
 };

 appState.clearModels({
     completeRegistration: {},
 });
 appState.registerViewLogic('completeRegistration', (ctx) => {
     ui_ctx = ctx;
     ui_ctx.fields.fullName.cols = 7;
     if (! authState.isModerated()) {
         ui_ctx.fields.reason.visible = false;
     }
 });

 authState.checkNeedsCompleteRegistration();
</script>
