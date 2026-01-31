<template>
    <div class="container-xl sr-fixed-lg">
        <VLoadingIndicator v-bind:message="loadingMessage" />
        <div v-if="materialCount === 0">
            <p class="lead text-center">Welcome to the Material Database</p>
        </div>
        <div class="row">
            <div class="col-sm-8">
                <VCortexCard title="Your Materials" v-show="materialCount">
                    <VMaterialTable v-on:materialCount="updateMaterialCount" />
                </VCortexCard>
                <VCortexCard title="Featured Materials">
                    some stuff here
                    <div class="float-end">
                        <a href>All Materials</a>
                    </div>
                </VCortexCard>
            </div>
            <div
                class="col-sm-4"
                v-show="materialCount !== undefined"
            >
                <VImportXLSXPanel />
            </div>
        </div>
    </div>
</template>

<script setup>
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VImportXLSXPanel from '@/apps/cortex/VImportXLSXPanel.vue';
 import VLoadingIndicator from '@/components/VLoadingIndicator.vue';
 import VMaterialTable from '@/apps/cortex/VMaterialTable.vue';
 import { ref } from 'vue';

 const materialCount = ref(0);
 const loadingMessage = ref('');

 const updateMaterialCount = (size) => {
     loadingMessage.value = size === undefined ? 'Connecting to the database' : '';
     materialCount.value = size;
 };
</script>
