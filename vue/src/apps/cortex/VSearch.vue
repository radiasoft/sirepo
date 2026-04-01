<template>
    <div class="container-xl sr-fixed-lg">
        <VLoadingIndicator v-bind:message="loadingMessage" />
        <div v-if="materialCount === 0">
            <p class="lead text-center">Welcome to the Material Database</p>
        </div>
        <div class="row">
            <div class="col-sm-8">
                <div v-if="featuredMaterials">
                    <VFeaturedMaterials v-bind:rows="featuredMaterials" />
                </div>
            </div>
            <div
                v-show="materialCount !== undefined"
                v-bind:class="{
                    'col-sm-4': featuredMaterials,
                    'col-sm-6 offset-sm-3': ! featuredMaterials,
                }"
            >
                <VImportXLSXPanel />
            </div>
        </div>
        <div class="p-3" v-if="! featuredMaterials"></div>
        <div class="row">
            <div v-show="materialCount" class="col-sm-12">
                <VCortexCard title="Your Materials" v-show="materialCount">
                    <VMaterialTable v-on:materialCount="updateMaterialCount" />
                </VCortexCard>
            </div>
        </div>
    </div>
</template>

<script setup>
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VFeaturedMaterials from '@/apps/cortex/VFeaturedMaterials.vue';
 import VImportXLSXPanel from '@/apps/cortex/VImportXLSXPanel.vue';
 import VLoadingIndicator from '@/components/VLoadingIndicator.vue';
 import VMaterialTable from '@/apps/cortex/VMaterialTable.vue';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted } from 'vue';
 import { ref } from 'vue';

 const materialCount = ref(0);
 const loadingMessage = ref('');
 const featuredMaterials = ref(null);

 const updateMaterialCount = (size) => {
     loadingMessage.value = size === undefined ? 'Connecting to the database' : '';
     materialCount.value = size;
 };

 onMounted(async () => {
     featuredMaterials.value = (await db.featuredMaterials()).rows;
     if (featuredMaterials.value && ! featuredMaterials.value.length) {
         featuredMaterials.value = null;
     }
 });

</script>
