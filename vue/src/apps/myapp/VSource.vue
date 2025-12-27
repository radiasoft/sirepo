<template>
    <VMasonry>
        <VCol>
            <VCard :viewName="viewName">
                <VForm :viewName="viewName" fieldDef="basic" />
            </VCard>
        </VCol>
        <VCol>
            <VCard viewName="heightWeightReport">
                <VPlot viewName="heightWeightReport"></VPlot>
            </VCard>
        </VCol>
    </VMasonry>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCol from '@/components/layout/VCol.vue';
 import VForm from '@/components/VForm.vue';
 import VPlot from '@/components/plot/VPlot.vue';
 import VMasonry from '@/components/layout/VMasonry.vue';

 const viewName = "dog";
</script>
