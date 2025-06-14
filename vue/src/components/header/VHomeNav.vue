<template>
    <ul class="navbar-nav">
        <li class="nav-item">
            <RouterLink
                class="nav-link"
                :class="{ active: ! isLoadedRef }"
                :to="{
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
    <ul class="navbar-nav ms-auto" v-if="! isLoadedRef">
        <li class="nav-item">
            <a
                class="nav-link"
                href
                @click.prevent="newSimulation"
            >
                <span class="bi bi-file-earmark-plus sr-nav-icon"></span>
                New Simulation
            </a>
        </li>
        <li class="nav-item">
            <a
                class="nav-link"
                href
                @click.prevent="newFolder"
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
        v-if="! isLoadedRef"
        viewName="simulation"
        title="New Simulation"
        ref="newModal"
    />
</template>

<script setup>
 import VBrand from '@/components/header/VBrand.vue';
 import VFormModal from '@/components/VFormModal.vue';
 import { RouterLink } from 'vue-router';
 import { appState, MODEL_CHANGED_EVENT } from '@/services/appstate.js';
 import { onMounted, onUnmounted, ref, watch } from 'vue';
 import { pubSub } from '@/services/pubsub.js';
 import { requestSender } from '@/services/requestsender.js';
 import { simManager } from '@/services/simmanager.js';

 const folderPath = ref('');
 const isLoadedRef = appState.isLoadedRef;
 const newModal = ref(null);

 const newFolder = () => {};

 const newSimulation = () => {
     if (isLoadedRef.value) {
         throw new Error('newSimulation expects an unloaded state');
     }
     appState.clearModels({
         simulation: appState.setModelDefaults({
             folder: simManager.getFolderPath(simManager.selectedFolder),
         }, 'simulation'),
     });
     newModal.value.showModal();
 };

 watch(isLoadedRef, (v) => {
     if (isLoadedRef.value) {
         folderPath.value = simManager.formatFolderPath(appState.models.simulation.folder);
     }
 });

 const onModelChanged = (names) => {
     if (! isLoadedRef.value && names[0] === 'simulation') {
         // call newSimulation
         appState.models.simulation.folder = simManager.getFolderPath(simManager.selectedFolder);
         requestSender.sendRequest(
             'newSimulation',
             (response) => {
                 //TODO(pjm): implement response handling
             },
             appState.models.simulation,
         );
         // add sim to simManager
         // call openSim
     }
 };

 onMounted(() => {
     pubSub.subscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

 onUnmounted(() => {
     pubSub.unsubscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

</script>
