
<template>
    <VNavHolder>
        <VBrand />
        <VHomeNav v-if="authState.isLoggedIn"/>
        <VSimNav v-if="isLoaded" />
        <VHelpAndLogout />
    </VNavHolder>
</template>

<script setup>
 import VBrand from '@/components/nav/VBrand.vue';
 import VHelpAndLogout from '@/components/nav/VHelpAndLogout.vue';
 import VHomeNav from '@/components/nav/VHomeNav.vue';
 import VNavHolder from '@/components/nav/VNavHolder.vue';
 import VSimNav from '@/components/nav/VSimNav.vue';
 import { authState } from '@/services/authstate.js';
 import { appState } from '@/services/appstate.js';

 const isLoaded = appState.isLoadedRef;
</script>
