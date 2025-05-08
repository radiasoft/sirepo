<template>
    <div class="container-fluid">
        <HelloWorld msg="some text" />
        <div class="links">
            <RouterLink :to="{ name: 'home' }">{{ routes.home.title }}</RouterLink>
            <RouterLink :to="{ name: 'test' }">{{ routes.test.title }}</RouterLink>
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

<script setup>
 import HelloWorld from '@/components/HelloWorld.vue'
 import router from '@/services/router'
 import { RouterLink, RouterView } from 'vue-router'
 import { appState } from '@/services/appstate.js';
 import { routes } from '@/services/router'

 //TODO(pjm): move schema and data to server call
 appState.schema = {
     enum: {
         DogDisposition: [
             ["aggressive", "Aggressive"],
             ["friendly", "Friendly"],
             ["submissive", "Submissive"]
         ],
         Gender: [
             ["male", "Male"],
             ["female", "Female"]
         ],
     },
     model: {
         dog: {
             breed: ["Breed", "String"],
             gender: ["Gender", "Gender", "male"],
             height: ["Height [cm]", "Float", 50.0, "Distance from front paws to withers"],
             weight: ["Weight [lbs]", "Float", 60.5],
             disposition: ["Disposition", "DogDisposition", "friendly"],
             favoriteTreat: ["Favorite Treat", "OptionalString", ""],
         },
         heightWeightReport: {}
     },
     view: {
         dog: {
             title: "Dog",
             basic: [
                 "breed",
                 "weight",
                 "height",
                 "disposition",
                 "favoriteTreat",
             ],
             advanced: [
                 "breed",
                 "gender",
                 "weight",
                 "height",
             ],
         },
         heightWeightReport: {
             title: "Physical Characteristics",
             advanced: [],
         },
     },
 };

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
