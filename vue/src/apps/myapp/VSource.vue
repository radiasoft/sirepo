<template>
    <VMasonry>
        <VCol>
            <VCard viewName="dog">
                <VForm viewName="dog" fieldDef="basic" />
            </VCard>
        </VCol>
        <VCol>
            <VCard viewName="heightWeightReport">
                <VPlot viewName="heightWeightReport"></VPlot>
            </VCard>
        </VCol>
        <VCol>
            <VCard viewName="simulationStatus">
                <VRunSim v-bind:sim="sim" viewName="activityAnimation"></VRunSim>
            </VCard>
        </VCol>
        <VCol v-for="report in sim.reports"">
            <VCard v-bind:viewName="report.modelName">
                <VFramePlot v-bind:sim="sim" v-bind:viewName="report.modelName"></VFramePlot>
            </VCard>
        </VCol>
    </VMasonry>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCol from '@/components/layout/VCol.vue';
 import VForm from '@/components/VForm.vue';
 import VFramePlot from '@/components/plot/VFramePlot.vue';
 import VMasonry from '@/components/layout/VMasonry.vue';
 import VPlot from '@/components/plot/VPlot.vue';
 import VRunSim from '@/components/VRunSim.vue';
 import { ref } from 'vue';

 const sim = ref({});
</script>
