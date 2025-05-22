<template>
    <component :is="loginComponent"></component>
</template>

<script setup>
 import VLoginEmail from '@/components/VLoginEmail.vue';
 import VLoginGuest from '@/components/VLoginGuest.vue';
 import VLoginLDAP from '@/components/VLoginLDAP.vue';
 import router from '@/services/router.js';
 import { appState } from '@/services/appstate.js';
 import { authState } from '@/services/authstate.js';

 let loginComponent;

 if (authState.isLoggedIn) {
     //TODO(pjm): root uri
     router.replace('/' + appState.simulationType);
 }
 else {
     if (! authState.visibleMethods.length === 1) {
         throw new Error(
             `authState.visibleMethods must contain only one login method: ${authState.visibleMethods}`,
         );
     }
     loginComponent = {
         email: VLoginEmail,
         guest: VLoginGuest,
         ldap: VLoginLDAP,
     }[authState.visibleMethods[0]];
     if (! loginComponent) {
         throw new Error(`Unsupported login method: ${authState.visibleMethods[0]}`);
     }
 }
</script>
