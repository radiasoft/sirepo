<template>
    <div class="row">
        <div class="col-sm-11 col-md-9">
            <div class="row">
                <div class="col-sm-7 offset-sm-5">
                    <h2>Moderation Request</h2>
                    <VForm v-if="! submitted" viewName="moderationRequest" fieldDef="basic" :wantButtons="false">
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
                    <div v-if="submitted"><p>Response submitted.</p></div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
 import VForm from '@/components/VForm.vue';
 import { appState } from '@/services/appstate.js';
 import { ref } from 'vue';
 import { requestSender } from '@/services/requestsender.js';

 const submitted = ref(false);
 let ui_ctx;

 const canSubmit = () => {
     return ui_ctx.fields.reason.val && ! ui_ctx.fields.reason.invalid;
 }

 const submitForm = () => {
     const handleResponse = (response) => {
         console.log('response:', response);
         if (response.state === 'error') {
             ui_ctx.fields.reason.val = '';
             ui_ctx.fields.reason.error = response.error;
         }
     };
     submitted.value = true;
     requestSender.sendRequest(
         'saveModerationReason',
         handleResponse,
         {
             reason: ui_ctx.fields.reason.val,
         },
         handleResponse,
     );
 };

 appstate.clearModels({
     moderationRequest: {},
 });
 appState.registerViewLogic('moderationRequest', (ctx) => {
     ui_ctx = ctx;
 });
</script>
