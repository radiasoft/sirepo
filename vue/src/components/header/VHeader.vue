
<template>
    <nav class="navbar border-bottom navbar-expand-sm static-top bg-light navbar-light">
        <div class="container-fluid">
            <VBrand />
            <VHomeNav />
            <VSimNav />
            <VHelpAndLogout />
        </div>
    </nav>
</template>

<script setup>
 import VBrand from '@/components/header/VBrand.vue';
 import VHelpAndLogout from '@/components/header/VHelpAndLogout.vue';
 import VHomeNav from '@/components/header/VHomeNav.vue';
 import VSimNav from '@/components/header/VSimNav.vue';
</script>
