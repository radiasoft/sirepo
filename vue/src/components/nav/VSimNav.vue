<template>
    <ul class="navbar-nav me-auto">
        <li class="nav-item nav-text">
            <a class="nav-link" href v-on:click.prevent="editSim">
                <span class="bi bi-pencil-fill sr-nav-icon"></span> <strong>{{ simName }}</strong>
            </a>
        </li>
    </ul>
    <ul class="navbar-nav nav-tabs">
        <template
            v-for="r in appRoutes"
            v-bind:key="r.name"
        >
            <li
                class="nav-item"
                v-if="showRoute[r.name]"
            >
                <RouterLink
                    class="nav-link"
                    activeClass="active"
                    v-bind:to="{
                         name: r.name,
                         params: {
                             simulationId: appState.models.simulation.simulationId,
                         },
                    }"
                >
                    <span
                        class="bi sr-nav-icon"
                        v-bind:class="r.tabIconClass"
                    ></span>
                    {{ r.tabName }}
                </RouterLink>
            </li>
        </template>
    </ul>
    <ul class="navbar-nav">
        <li class="nav-item nav-text">
            <a class="nav-link" href v-on:click.prevent="openDocumentation">
                <span class="bi bi-book sr-nav-icon"></span>
                Notes
            </a>
        </li>

        <!--
        <li data-settings-menu="nav">
            <app-settings data-ng-transclude="appSettingsSlot"></app-settings>
        </li>
        -->
    </ul>

    <VFormModal
        viewName="simulation"
        v-bind:title="strings.formatKey('simulationDataType')"
        ref="editModal"
    />
</template>

<script setup>
 import VFormModal from '@/components/VFormModal.vue';
 import { RouterLink } from 'vue-router';
 import { appResources } from '@/services/appresources.js';
 import { appState } from '@/services/appstate.js';
 import { reactive, ref } from 'vue';
 import { strings } from '@/services/strings.js';
 import { useModelChanged } from '@/components/useModelChanged.js';

 const editModal = ref(null);
 const simName = ref(null);
 const appRoutes = appResources.getAppRoutes();
 const showRoute = reactive(Object.fromEntries(
     appRoutes.map((r) => [r.name, true]),
 ));

 const editSim = () => {
     editModal.value.showModal();
 };

 const openDocumentation = () => {
 };

 const update = () => {
     simName.value = appState.models.simulation.name;
     for (const r of appRoutes) {
         if (r.tabVisible) {
             showRoute[r.name] = r.tabVisible();
         }
     }
 };

 useModelChanged(update);

 update();
</script>
