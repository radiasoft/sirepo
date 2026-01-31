<template>
    <div v-if="material" class="container-lg sr-fixed-lg">
        <div class="float-end">
            <VNavButton
                v-bind:active="selectedSection"
                section="overview"
                label="Overview"
                v-on:selected="selectSection"
            ></VNavButton>
            <VNavButton
                v-if="material.properties.length"
                v-bind:active="selectedSection"
                section="properties"
                label="Properties"
                v-on:selected="selectSection"
            ></VNavButton>
            <div class="btn-group">
                <VNavButton
                    v-bind:active="selectedSection"
                    section="neutronics"
                    label="Neutronics"
                    v-on:selected="selectSection"
                ></VNavButton>
                <button
                    class="btn dropdown-toggle dropdown-toggle-split"
                    v-bind:class="{
                        active: isSelected('neutronics'),
                        'btn-primary': isSelected('neutronics'),
                        'btn-light': ! isSelected('neutronics'),
                    }"
                    data-bs-toggle="dropdown"
                ></button>
                <ul class="dropdown-menu dropdown-menu-end" id="sr-neutronics-dropdown-menu">
                    <li v-for="sim in Object.keys(neutronicsSims)">
                        <button class="dropdown-item" v-on:click="selectNeutronics(sim)">
                            {{ neutronicsSims[sim] }}
                        </button>
                    </li>
                </ul>
            </div>
        </div>
        <div class="h2">{{ material.name }}</div>
    </div>
    <div v-if="material">
        <div v-if="isSelected('neutronics')">
            <VNeutronics
                v-bind:materialId="materialId"
                v-bind:neutronics="neutronicsSim"
                v-bind:title="neutronicsSims[neutronicsSim]"
            />
        </div>
        <div class="container-lg sr-fixed-lg">
            <div v-if="isSelected('overview')">
                <VOverview v-bind:material="material" />
            </div>
            <div v-if="isSelected('properties')">
                <VProperties v-bind:material="material" />
            </div>
        </div>
    </div>
</template>

<script setup>
 import VNavButton from '@/apps/cortex/VNavButton.vue';
 import VNeutronics from '@/apps/cortex/VNeutronics.vue';
 import VOverview from '@/apps/cortex/VOverview.vue';
 import VProperties from '@/apps/cortex/VProperties.vue';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, ref } from 'vue';
 import { useRoute } from 'vue-router';

 const neutronicsSims = {
     tileAnimation: 'Homogeneous Tile',
 };

 const material = ref(null);
 const materialId = ref(null);
 const route = useRoute();
 // overview, properties, neutronics
 const selectedSection = ref('overview');
 const neutronicsSim = ref(Object.keys(neutronicsSims)[0]);

 const isSelected = (section) => {
     return selectedSection.value === section;
 };

 const selectNeutronics = (neutronics) => {
     neutronicsSim.value = neutronics;
     selectSection('neutronics');
 }

 const selectSection = (section) => {
     selectedSection.value = section;
     // bootstrap dropdown doesn't always dismiss correctly when navigating buttons
     const d = document.getElementById('sr-neutronics-dropdown-menu')
     if (d && d.classList) {
         d.classList.remove('show');
     }
 };

 onMounted(async () => {
     materialId.value = route.params.materialId;
     material.value = await db.materialDetail(materialId.value);
 });
</script>

<style scoped>
 .sr-fixed-lg {
     max-width: 1200px;
 }
</style>
