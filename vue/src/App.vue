<template>
    <VHeader />
    <br />
    <div class="container-fluid">
        <RouterView />
    </div>
</template>

<script setup>
 import VHeader from '@/components/VHeader.vue';
 import { RouterView } from 'vue-router';
</script>
