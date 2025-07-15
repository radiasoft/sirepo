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
                {{ strings.formatKey('simulationDataTypePlural') }}
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
                {{ strings.newSimulationLabel() }}
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
        v-bind:title="strings.newSimulationLabel()"
        ref="newSimModal"
    />
    <VFormModal
        v-if="! isLoaded"
        viewName="simFolder"
        title="New Folder"
        ref="simFolderModal"
    />
</template>

<script setup>
 import VFormModal from '@/components/VFormModal.vue';
 import { RouterLink } from 'vue-router';
 import { appState } from '@/services/appstate.js';
 import { ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { simManager } from '@/services/simmanager.js';
 import { strings } from '@/services/strings.js';
 import { uri } from '@/services/uri.js';
 import { useSimModal } from '@/components/nav/useSimModal.js';

 const folderPath = ref('');
 const isLoaded = appState.isLoadedRef;

 const { modalRef: simFolderModal, showModal: newFolder } = useSimModal(
     'simFolder',
     () => ({
         parent: simManager.getFolderPath(simManager.selectedFolder),
     }),
     (simFolder) => {
         simManager.addFolder(
             simFolder.parent,
             simFolder.name,
         )
     },
 );

 const { modalRef: newSimModal, showModal: newSimulation } = useSimModal(
     'simulation',
     () => ({
         folder: simManager.getFolderPath(simManager.selectedFolder),
     }),
     async (simulation) => {
         if (! isLoaded.value) {
             // call newSimulation
             simulation.folder = simManager.getFolderPath(simManager.selectedFolder);
             const r = await requestSender.sendRequest(
                 'newSimulation',
                 simulation,
             );
             //TODO(pjm): add sim to simManager
             uri.localRedirectHome(r.models.simulation.simulationId);
         }
     },
 );

 watch(isLoaded, (v) => {
     if (isLoaded.value) {
         folderPath.value = simManager.formatFolderPath(appState.models.simulation.folder);
     }
 });

</script>
