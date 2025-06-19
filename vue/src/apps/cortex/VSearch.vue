<template>
    <div class="row">
        <div class="col-sm-8 col-lg-6 offset-lg-2">
            <VMaterialTable />
        </div>
        <div class="col-sm-4 col-lg-3 offset-lg-1">
            <VImportXLSPanel />
        </div>
    </div>
</template>

<script setup>
 import VImportXLSPanel from '@/apps/cortex/VImportXLSPanel.vue';
 import VMaterialTable from '@/apps/cortex/VMaterialTable.vue';
</script>
