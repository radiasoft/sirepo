
<template>
    <div class="row text-center">
        <p>Please click the button below to complete the login process.</p>
        <p>
            <button class="btn btn-primary" type="button" @click="confirm">Confirm</button>
        </p>
        <div v-if="message" class="col-md-8 offset-md-2">
            <VWell>{{ message }}</VWell>
        </div>
    </div>
</template>

<script setup>
 import VWell from '@/components/layout/VWell.vue';
 import { authState } from '@/services/authstate.js';
 import { ref } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { useRoute } from 'vue-router';

 const route = useRoute();
 const message = ref('');

 const confirm = async () => {
     const r = await requestSender.sendRequest(
         'authEmailAuthorized',
         {
             token: route.params.token,
         },
     );
     message.value = authState.handleLogin(r);
 };
</script>
