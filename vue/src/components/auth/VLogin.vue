<template>
    <component v-bind:is="loginComponent"></component>
</template>

<script setup>
 import VLoginEmail from '@/components/auth/VLoginEmail.vue';
 import VLoginGuest from '@/components/auth/VLoginGuest.vue';
 import VLoginLDAP from '@/components/auth/VLoginLDAP.vue';
 import { appState } from '@/services/appstate.js';
 import { authState } from '@/services/authstate.js';
 import { router }  from '@/services/router.js';

 let loginComponent;

 if (authState.checkNeedLogin()) {
     const m = authState.getAuthMethod();
     loginComponent = {
         email: VLoginEmail,
         guest: VLoginGuest,
         ldap: VLoginLDAP,
     }[m];
     if (! loginComponent) {
         throw new Error(`Unsupported login method: ${m}`);
     }
 }
</script>
