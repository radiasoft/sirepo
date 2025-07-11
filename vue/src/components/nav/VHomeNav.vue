<template>
    <ul class="navbar-nav">
        <li class="nav-item">
            <RouterLink
                class="nav-link"
                v-bind:class="{ active: ! isLoaded }"
                v-bind:to="{
                    name: 'simulations',
                    params: {
                        folderPath: folderPath,
                    },
                }"
            >
                <span class="bi bi-list-task sr-nav-icon"></span>
                Simulations
            </RouterLink>
        </li>
    </ul>
    <ul class="navbar-nav ms-auto" v-if="! isLoaded">
        <li class="nav-item">
            <a
                class="nav-link"
                href
                v-on:click.prevent="newSimulation"
            >
                <span class="bi bi-file-earmark-plus sr-nav-icon"></span>
                New Simulation
            </a>
        </li>
        <li class="nav-item">
            <a
                class="nav-link"
                href
                v-on:click.prevent="newFolder"
            >
                <span class="bi bi-folder-plus sr-nav-icon"></span>
                New Folder
            </a>
        </li>

        <!--
        <app-header-right-sim-list>
            <ul class="nav navbar-nav sr-navbar-right">
                <li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
            </ul>
        </app-header-right-sim-list>
        -->

    </ul>
    <VFormModal
        v-if="! isLoaded"
        viewName="simulation"
        title="New Simulation"
        ref="newModal"
    />
</template>

<script setup>
 import VBrand from '@/components/nav/VBrand.vue';
 import VFormModal from '@/components/VFormModal.vue';
 import { RouterLink } from 'vue-router';
 import { appState, MODEL_CHANGED_EVENT } from '@/services/appstate.js';
 import { onMounted, onUnmounted, ref, watch } from 'vue';
 import { pubSub } from '@/services/pubsub.js';
 import { requestSender } from '@/services/requestsender.js';
 import { simManager } from '@/services/simmanager.js';
 import { uri } from '@/services/uri.js';

 const folderPath = ref('');
 const isLoaded = appState.isLoadedRef;
 const newModal = ref(null);

 const newFolder = () => {};

 const newSimulation = async () => {
     if (isLoaded.value) {
         throw new Error('newSimulation expects an unloaded state');
     }
     await appState.clearModels({
         simulation: appState.setModelDefaults({
             folder: simManager.getFolderPath(simManager.selectedFolder),
         }, 'simulation'),
     });
     newModal.value.showModal();
 };

 watch(isLoaded, (v) => {
     if (isLoaded.value) {
         folderPath.value = simManager.formatFolderPath(appState.models.simulation.folder);
     }
 });

 const onModelChanged = async (names) => {
     if (names[0] === 'simulation') {
         if (isLoaded.value) {
             folderPath.value = simManager.formatFolderPath(appState.models.simulation.folder);
         }
         else {
             // call newSimulation
             appState.models.simulation.folder = simManager.getFolderPath(simManager.selectedFolder);
             const r = await requestSender.sendRequest(
                 'newSimulation',
                 appState.models.simulation,
             );
             //TODO(pjm): add sim to simManager
             uri.localRedirectHome(r.models.simulation.simulationId);
         }
     }
 };

 onMounted(() => {
     pubSub.subscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

 onUnmounted(() => {
     pubSub.unsubscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

</script>
