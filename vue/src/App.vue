<template>
    <component :is="headerComponent" />
    <br />
    <div class="container-fluid">
        <RouterView />
    </div>
</template>

<script setup>
 import { appResources } from '@/services/appresources.js';
 import { RouterView } from 'vue-router';

 const headerComponent = appResources.headerComponent();
</script>
