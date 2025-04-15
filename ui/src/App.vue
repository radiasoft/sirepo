<script setup>
 import { RouterLink, RouterView } from 'vue-router'
 import HelloWorld from '@/components/HelloWorld.vue'
 import router from './router'
 import { routes } from './router'
</script>

<template>
    <div>
        <HelloWorld msg="some text" />

        <div class="links">
            <RouterLink :to="routes.HOME.path">{{ routes.HOME.name }}</RouterLink>
            <RouterLink :to="routes.ABOUT.path">{{ routes.ABOUT.name }}</RouterLink>
        </div>
    </div>
    <RouterView />
</template>

<style scoped>
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
