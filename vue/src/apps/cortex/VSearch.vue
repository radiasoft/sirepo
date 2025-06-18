<template>
    <div class="row">
        <div class="col-sm-8 col-lg-6 offset-lg-2">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Material Name</th>
                        <th>Date Uploaded</th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="mat in state.materials"
                        :key="mat.simulationId"
                    >
                        <td>{{ mat.name }}</td>
                        <td>{{ formatDate(mat.lastModified) }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="col-sm-4 col-lg-3 offset-lg-1">
            <VImportXLSPanel />
        </div>
    </div>
</template>

<script setup>
 import VImportXLSPanel from '@/apps/cortex/VImportXLSPanel.vue';
 import { appState } from '@/services/appstate.js';
 import { onMounted, reactive } from 'vue';
 import { simManager } from '@/services/simmanager.js';

 const dateFormat = Intl.DateTimeFormat('en-US', {
     year: 'numeric',
     month: 'short',
     day: 'numeric',
     hour: 'numeric',
     minute: 'numeric',
 });
 const formatDate = (value) => dateFormat.format(value);
 const state = reactive({
     materials: [],
 });

 onMounted(async () => {
     appState.clearModels();
     await simManager.getSims();
     state.materials = simManager.openFolder('').children.filter((n) => ! n.isFolder);
 });
</script>
