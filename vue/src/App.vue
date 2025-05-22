<template>
    <VHeader />
    <div class="container-fluid">
        <div class="links">
            <!-- testing links only -->
            <RouterLink :to="{ name: 'home', params: { simulationType: appState.simulationType }}">Home</RouterLink>
            <RouterLink :to="{ name: 'test', params: { simulationType: appState.simulationType }}">Test</RouterLink>
            <RouterLink :to="{ name: 'about', params: { simulationType: appState.simulationType }}">About</RouterLink>
        </div>
        <RouterView />
    </div>
</template>

<style scoped>
 .links {
     padding-bottom: 1em;
 }
 .links a {
     margin: 1ex;
 }
 a {
     color: blue;
     text-decoration: none;
 }
 a.router-link-active {
     color: black;
 }
</style>

<script setup>
 import VHeader from '@/components/VHeader.vue';
 import { RouterLink, RouterView } from 'vue-router';
 import { appState } from '@/services/appstate.js';
 import { routes } from '@/services/router.js';
 import router from '@/services/router.js';

 //TODO(pjm): change to server call from route
 appState.loadModels({
     dog: {
         breed: 'Poodle',
         gender: 'female',
         weight: 25.6,
         height: 34.7,
         disposition: "submissive",
         favoriteTreat: "hotdogs",
     },
     simulation: {
         simulationId: '12345678',
     },
 });
</script>
