<template>
    <div class="col-md-8 offset-md-2">
        <VWell>
            <p>{{ message() }}</p>
            <RouterLink v-bind:to="{ name: 'login', params: { simulationType: schema.simulationType }}">
                Please try to login again.
            </RouterLink>
        </VWell>
    </div>
</template>

<script setup>
 import VWell from '@/components/layout/VWell.vue';
 import { RouterLink, useRoute } from 'vue-router';
 import { schema } from '@/services/schema.js';

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
