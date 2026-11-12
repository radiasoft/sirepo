<template>
    <div class="row">
        <div class="col-sm-11 col-md-9">
            <div class="row">
                <div class="col-sm-7 offset-sm-5">
                    <p>Enter your <strong>institutional email address</strong>. Any email or internet address associated with providers like Gmail.com, Yahoo.com, Outlook.com, etc. will be rejected. Emails associated with <a href="https://www.state.gov/countries-of-particular-concern-special-watch-list-countries-entities-of-particular-concern" target="_blank">'Countries of Particular Concern' as designated by the US State Department</a> will also be rejected.</p>
                </div>
            </div>
            <VForm viewName="emailLogin" fieldDef="basic" v-bind:wantButtons="false">
                <div class="row">
                    <div class="col-sm-7 offset-sm-5">
                        <p><button
                               class="btn btn-primary sr-button-save-cancel"
                               v-bind:disabled="isBusy"
                               v-on:click="submitForm"
                           >
                            Continue
                        </button></p>
                    </div>
                    <div class="col-sm-7 offset-sm-5">
                        <p>When you click continue, we'll send an authorization link to your inbox.</p>
                        <p>By signing up for Sirepo you agree to Sirepo's <a href="/en/privacy.html" target="_blank">privacy policy</a> and <a href="/en/terms.html" target="_blank">terms and conditions</a>, and to receive informational and marketing communications from RadiaSoft. You may unsubscribe at any time.</p>
                    </div>
                </div>
            </VForm>
        </div>
    </div>
    <VConfirmationModal ref="confirm" title="Check your inbox" v-bind:canDismiss="false">
        We just emailed a confirmation link to {{ ui_ctx.fields.email.val }}. Click the link and you'll be signed in. You may close this window.
    </VConfirmationModal>
</template>

<script setup>
 import VConfirmationModal from '@/components/VConfirmationModal.vue';
 import VForm from '@/components/VForm.vue';
 import { appResources } from '@/services/appresources.js';
 import { appState } from '@/services/appstate.js';
 import { ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { schema } from '@/services/schema.js';

 const confirm = ref(null);
 const isBusy = ref(false);
 let ui_ctx;

 const isInvalid = () => ! ui_ctx.fields.email.val || ui_ctx.fields.email.invalid;

 const submitForm = async () => {
     if (isInvalid()) {
         ui_ctx.fields.email.error = 'Email address is invalid. Please update and resubmit.';
         return;
     }
     isBusy.value = true;
     const r = await requestSender.sendRequest(
         'authEmailLogin',
         {
             email: ui_ctx.fields.email.val,
         },
     );
     isBusy.value = false;
     if (r.state === 'ok') {
         confirm.value.showModal();
         return;
     }
     ui_ctx.fields.email.val = '';
     //TODO(pjm): share message with authState
     ui_ctx.fields.email.error = r.error
         || `Server reported an error, please contact ${schema.feature_config.support_email}`;
 };

 appState.clearModels({
     emailLogin: {},
 });

 appResources.registerViewLogic('emailLogin', (ctx) => {
     ui_ctx = ctx;
     ui_ctx.fields.email.cols = 7;
     watch(ui_ctx, () => {
         if (! isInvalid()) {
             ui_ctx.fields.email.error = '';
         }
     });
 });
</script>
