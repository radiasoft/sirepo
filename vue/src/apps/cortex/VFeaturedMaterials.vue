<template>
    <VCortexCard
        title="Featured Materials"
        v-show="featured.length"
    >
        <div class="row ps-5 pe-5">
            <div
                class="col-sm-4"
                v-for="f in featured"
            >
                <button class="w-100 btn btn-outline-primary">
                    <div class="cortex-material-button pt-3">
                    <span class="cortex-material-icon bi bi-database"></span>
                    <h5>{{ f.name }}</h5>
                    <p class="Card-text">
                        {{ f.is_plasma_facing ? 'plasma-facing' : 'structural' }}
                    </p>
                    </div>
                </button>
            </div>
        </div>
    </VCortexCard>
</template>

<script setup>
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import { ref } from 'vue';

 const featured = ref([
     {
         name: 'Ditungsten Carbide',
         is_plasma_facing: true,
     },
     {
         name: 'Stainless Steel 316',
         is_plasma_facing: false,
     },
     {
         name: 'Tungsten Carbide with Iron and Chromium Binding',
         is_plasma_facing: false,
     },
 ]);
</script>

<style scoped>
 .cortex-material-button {
     min-height: 13em;
     width: 100%;
     color: black;
 }
 .cortex-material-button:hover {
     color: white;
 }
 .cortex-material-icon {
     font-size: 2rem;
 }
</style>
