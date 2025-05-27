<template>
    <div class="row">
        <div class="col-sm-6 offset-sm-3">
            <VWell>{{ message }}</VWell>
        </div>
    </div>
</template>

<script setup>
 import VWell from '@/components/layout/VWell.vue';
 import { appState } from '@/services/appstate.js';
 import { authState } from '@/services/authstate.js';
 import { ref } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { useRouter } from 'vue-router';

 const message = ref('Creating your account. Please wait...');
 const router = useRouter();

 const handleResponse = (response) => {
     message.value = authState.handleLogin(response);
 };

 requestSender.sendRequest(
     'authGuestLogin',
     handleResponse,
     {},
     handleResponse,
 );
</script>
