<template>
    <ul class="navbar-nav me-auto" v-if="isLoaded">
        <li class="nav-item nav-text">
            <a class="nav-link" href @click.prevent="editSimulation">
                <span class="bi bi-pencil-fill sr-nav-icon"></span> <strong>{{ simName }}</strong>
            </a>
        </li>
    </ul>
    <ul class="navbar-nav nav-tabs" v-if="isLoaded">
        <template
            v-for="r in appRoutes"
            :key="r.name"
        >
            <li
                class="nav-item"
                v-if="showRoute[r.name]"
            >
                <RouterLink
                    class="nav-link"
                    activeClass="active"
                    :to="{
                         name: r.name,
                         params: {
                             simulationId: appState.models.simulation.simulationId,
                         },
                    }"
                >
                    <span
                        class="bi sr-nav-icon"
                        :class="r.tabIconClass"
                    ></span>
                    {{ r.tabName }}
                </RouterLink>
            </li>
        </template>
    </ul>
    <ul class="navbar-nav" v-if="isLoaded">
        <li class="nav-item nav-text">
            <a class="nav-link" href @click.prevent="openDocumentation">
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
        v-if="isLoaded"
        viewName="simulation"
        title="Simulation"
        ref="editModal"
    />
</template>

<script setup>
 import VFormModal from '@/components/VFormModal.vue';
 import { RouterLink } from 'vue-router';
 import { appResources } from '@/services/appresources.js';
 import { appState, MODEL_CHANGED_EVENT } from '@/services/appstate.js';
 import { onMounted, onUnmounted, reactive, ref, watch } from 'vue';
 import { pubSub } from '@/services/pubsub.js';

 const editModal = ref(null);
 const isLoaded = appState.isLoadedRef;
 const simName = ref(null);
 const appRoutes = appResources.getAppRoutes();
 const showRoute = reactive(Object.fromEntries(
     appRoutes.map((r) => [r.name, true]),
 ));

 const editSimulation = () => {
     editModal.value.showModal();
 };

 const update = () => {
     if (isLoaded.value) {
         simName.value = appState.models.simulation.name;
         for (const r of appRoutes) {
             if (r.tabVisible) {
                 showRoute[r.name] = r.tabVisible();
             }
         }
     }
     else {
         simName.value = null;
     }
 };

 const onModelChanged = (names) => {
     if (isLoaded.value) {
         update();
     }
 };

 const openDocumentation = () => {
 };

 watch(isLoaded, update);

 onMounted(() => {
     pubSub.subscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

 onUnmounted(() => {
     pubSub.unsubscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

</script>
