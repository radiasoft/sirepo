<template>
    <ul class="nav" v-bind:class="pills ? 'nav-pills' : 'nav-tabs'">
        <li class="nav-item" v-for="i in items" v-bind:key="i.value">
            <button
                type="button"
                class="nav-link"
                v-bind:class="{ active: i.value === model }"
                v-on:click="model = i.value"
            >
                {{ i.label }}
            </button>
        </li>
    </ul>
</template>

<script setup>
 // v-model is the value of the selected item
 const model = defineModel();

 defineProps({
     // [{ value, label }]
     items: { type: Array, required: true },
     pills: { type: Boolean, default: false },
 });
</script>
