<template>
    <div class="row">
        <div class="col-sm-6 offset-sm-3">
            <VWell>{{ message }}</VWell>
        </div>
    </div>
</template>

<script setup>
 import VWell from '@/components/layout/VWell.vue';
 import { authState } from '@/services/authstate.js';
 import { ref, onMounted } from 'vue';
 import { requestSender } from '@/services/requestsender.js';

 const message = ref('Creating your account. Please wait...');

 onMounted(async () => {
     const r = await requestSender.sendRequest('authGuestLogin', {});
     message.value = authState.handleLogin(response);
 });
</script>
