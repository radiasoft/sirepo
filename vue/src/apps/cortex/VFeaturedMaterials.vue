<template>
    <VCortexCard
        title="Featured Materials"
        v-show="rows.length"
    >
        <div class="row ps-5 pe-5">
            <div
                class="col-sm-4"
                v-for="f in rows"
            >
                <VMaterialLink
                    v-bind:materialId="f.material_id"
                    v-bind:isPublic="true"
                >
                    <button class="w-100 btn btn-outline-primary">
                        <div class="cortex-material-button pt-3">
                            <span class="cortex-material-icon bi bi-database"></span>
                            <h5>{{ f.material_name }}</h5>
                            <p class="Card-text">
                                {{ f.is_plasma_facing ? 'plasma-facing' : 'structural' }}
                            </p>
                        </div>
                    </button>
                </VMaterialLink>
            </div>
        </div>
    </VCortexCard>
</template>

<script setup>
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VMaterialLink from '@/apps/cortex/VMaterialLink.vue';
 import { ref } from 'vue';

 const props = defineProps({
     rows: Array,
 })
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
