
<template>
    <nav class="navbar border-bottom navbar-expand-sm static-top bg-light navbar-light">
        <div class="container-fluid">
            <VBrand />
            <VSimNav />
            <VHelpAndLogout />
        </div>
    </nav>
</template>

<script setup>
 import VBrand from '@/components/nav/VBrand.vue';
 import VHelpAndLogout from '@/components/nav/VHelpAndLogout.vue';
 import VSimNav from '@/components/nav/VSimNav.vue';
</script>
