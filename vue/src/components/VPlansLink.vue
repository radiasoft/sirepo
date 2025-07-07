<template>
    <a v-bind:href="plansUrl"><slot></slot></a>
</template>

<script setup>
 import { schema } from '@/services/schema.js';

 const plansUrl = schema.constants.plansUrl;
</script>
