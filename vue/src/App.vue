<script setup>
 import { RouterLink, RouterView } from 'vue-router'
 import HelloWorld from '@/components/HelloWorld.vue'
 import router from './router'
 import { routes } from './router'
</script>

<template>
    <div class="container-fluid">
        <HelloWorld msg="some text" />
        <div class="links">
            <RouterLink :to="{ name: 'home' }">{{ routes.home.title }}</RouterLink>
            <RouterLink :to="{ name: 'about' }">{{ routes.about.title }}</RouterLink>
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
