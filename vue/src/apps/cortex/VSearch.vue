<template>
    <div v-if="! materialCount">
        <p class="lead text-center">Welcome to the Material Database</p>
    </div>
    <div class="row">
        <div v-show="materialCount" class="col-sm-8 col-lg-6 offset-lg-2">
            <VMaterialTable @materialCount="updateMaterialCount" />
        </div>
        <div
            :class="{
                'col-sm-4 col-lg-3 offset-lg-1': materialCount > 0,
                'col-sm-4 offset-sm-4': materialCount === 0,
            }"
        >
            <VImportXLSPanel />
        </div>
    </div>
</template>

<script setup>
 import VImportXLSPanel from '@/apps/cortex/VImportXLSPanel.vue';
 import VMaterialTable from '@/apps/cortex/VMaterialTable.vue';
 import { ref } from 'vue';

 const materialCount = ref(0);

 const updateMaterialCount = (size) => materialCount.value = size;
</script>
