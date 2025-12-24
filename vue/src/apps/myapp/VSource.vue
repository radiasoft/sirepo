<template>
    <VMasonry>
        <VCol>
            <VCard :viewName="viewName">
                <VForm :viewName="viewName" fieldDef="basic" />
            </VCard>
        </VCol>
        <VCol>
            <VCard viewName="heightWeightReport">
                <VLine viewName="heightWeightReport">
                </VLine>
            </VCard>
        </VCol>
    </VMasonry>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCol from '@/components/layout/VCol.vue';
 import VForm from '@/components/VForm.vue';
 import VLine from '@/components/plot/VLine.vue';
 import VMasonry from '@/components/layout/VMasonry.vue';

 const viewName = "dog";
</script>
