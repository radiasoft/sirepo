<template>
    <div class="container-fluid">
        <HelloWorld msg="some text" />
        <div class="links">
            <!-- testing links only -->
            <RouterLink :to="{ name: 'home', params: { simulationType: appState.simulationType }}">{{ routes.home.title }}</RouterLink>
            <RouterLink :to="{ name: 'test', params: { simulationType: appState.simulationType }}">{{ routes.test.title }}</RouterLink>
            <RouterLink :to="{ name: 'about', params: { simulationType: appState.simulationType }}">{{ routes.about.title }}</RouterLink>
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
 import HelloWorld from '@/components/HelloWorld.vue'
 import { RouterLink, RouterView } from 'vue-router'
 import { appState } from '@/services/appstate.js';
 import { routes } from '@/services/router'

 //TODO(pjm): change to server call from route
 appState.loadModels({
     dog: {
         breed: 'Great Dane',
         gender: 'male',
         weight: 70.25,
         height: 81.28,
         disposition: "friendly",
         favoriteTreat: "",
     },
 });

</script>
