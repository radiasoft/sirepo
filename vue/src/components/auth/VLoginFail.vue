<template>
    <div class="col-md-8 offset-md-2">
        <VWell>
            <p>{{ message() }}</p>
            <a :href="uri.formatLocal('login')">Please try to login again.</a>
        </VWell>
    </div>
</template>

<script setup>
 import VWell from '@/components/layout/VWell.vue';
 import { uri } from '@/services/uri.js';
 import { useRoute } from 'vue-router';

 const route = useRoute();

 const message = () => {
     const { method, reason } = route.params;

     if (reason === 'deprecated' || reason === 'invalid-method') {
         return `You can no longer login with ${method}`;
     }
     if (reason === 'email-token') {
         return 'You clicked on an expired link.';
     }
     return 'Unexpected error.';
 }
</script>
