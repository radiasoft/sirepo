<template>
    <VCol>
        <VCard viewName="simulationStatus" v-bind:title="title">
            <div class="row">
                <div class="col-sm-7" v-if="isReady && ! hasPlots">
                    <VNeutronicsSim
                        v-bind:materialId="materialId"
                        v-bind:neutronics="neutronics"
                        v-on:simCompleted="loadAndRebuild()"
                    />
                </div>
                <div class="col-sm-5" v-if="neutronics == 'slabAnimation'">
                    <img  class="img-fluid" v-bind:src="slabUrl" alt="Slab" />
                </div>
            </div>
        </VCard>
    </VCol>
    <VCortexCard v-bind:title="sections[section]" v-for="section in Object.keys(reportsBySection)">
        <div class="row">
            <VCol v-for="report in reportsBySection[section]" v-bind:key="report.trackBy">
                <VCard
                    v-bind:viewName="report.viewName"
                    v-bind:title="report.title"
                    v-bind:canFullScreen="true"
                    v-bind:downloadActions="report.reportData.downloadActions"
                >
                    <VFramePlot
                        v-bind:modelName="report.modelName"
                        v-bind:reportData="report.reportData"
                    ></VFramePlot>
                </VCard>
            </VCol>
        </div>
    </VCortexCard>
</template>

<script setup>
 import VCard from '@/components/VCard.vue';
 import VCol from '@/components/layout/VCol.vue';
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VFramePlot from '@/components/plot/VFramePlot.vue';
 import VNeutronicsSim from '@/apps/cortex/VNeutronicsSim.vue';
 import slabUrl from '@/assets/cortex/slab.png';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, reactive, ref, watch } from 'vue';

 const props = defineProps({
     materialId: String,
     neutronics: String,
     title: String,
 });
 const reportsBySection = reactive({});
 const sections = {
     steady_state: 'Steady State',
     flux: 'ParticleFluxes',
     time_dependent: 'Time-Dependent Responses',
 };
 let allPlots;
 const hasPlots = ref(false);
 const isReady = ref(false);

 const rebuildReports = async () => {
     for (const v in sections) {
         reportsBySection[v] = [];
     }
     let i = 0;
     for (const r of allPlots || []) {
         if (r.meta.model !== props.neutronics) {
             continue;
         }
         reportsBySection[r.meta.section].push({
             modelName: r.meta.model,
             viewName: r.meta.model,
             trackBy: r.meta.model + r.meta.stat,
             reportData: r,
         });
     }
     for (const v in sections) {
         if (! reportsBySection[v].length) {
             delete reportsBySection[v];
         }
     }
     hasPlots.value = Boolean(Object.keys(reportsBySection).length);
     isReady.value = true;
 };

 const loadAndRebuild = async () => {
     allPlots = await db.loadPlots(props.materialId);
     await rebuildReports();
 };

 onMounted(async () => {
     await loadAndRebuild();
 });

 watch(() => props.neutronics, async () => {
     hasPlots.value = false;
     isReady.value = false;
     await rebuildReports();
 });

</script>
