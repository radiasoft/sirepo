<template>
    <VLoadingIndicator v-bind:message="loadingMessage" />
    <div v-if="materialCount === 0">
        <p class="lead text-center">Welcome to the Material Database</p>
    </div>
    <div class="row">
        <div v-show="materialCount" class="col-sm-8 col-lg-6 offset-lg-2">
            <VMaterialTable v-on:materialCount="updateMaterialCount" />
        </div>
        <div
            v-if="materialCount !== undefined"
            v-bind:class="{
                'col-sm-4 col-lg-3 offset-lg-1': materialCount > 0,
                'col-sm-6 offset-sm-3': materialCount === 0,
            }"
        >
            <VImportXLSXPanel />
        </div>
    </div>
</template>

<script setup>
 import VImportXLSXPanel from '@/apps/cortex/VImportXLSXPanel.vue';
 import VMaterialTable from '@/apps/cortex/VMaterialTable.vue';
 import VLoadingIndicator from '@/components/VLoadingIndicator.vue';
 import { ref } from 'vue';

 const materialCount = ref(0);
 const loadingMessage = ref('');

 const updateMaterialCount = (size) => {
     loadingMessage.value = size === undefined ? 'Connecting to the database' : '';
     materialCount.value = size;
 };
</script>
