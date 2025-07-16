
<template>
    <VNavHolder>
        <VBrand />
        <div class="navbar-nav ms-auto"></div>
        <VHelpAndLogout />
    </VNavHolder>
</template>

<script setup>
 import VBrand from '@/components/nav/VBrand.vue';
 import VHelpAndLogout from '@/components/nav/VHelpAndLogout.vue';
 import VNavHolder from '@/components/nav/VNavHolder.vue';
 import VSimNav from '@/components/nav/VSimNav.vue';
</script>
