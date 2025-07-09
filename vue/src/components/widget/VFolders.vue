<!--
   A list of available sim folders.
 -->
<template>
    <VSelect
        v-bind:field_name="field_name"
        v-bind:ui_ctx="ui_ctx"
    />
</template>

<script setup>
 import VSelect from '@/components/widget/VSelect.vue';
 import { simManager } from '@/services/simmanager.js';

 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });

 simManager.getSims().then(() => {
     const f = props.ui_ctx.fields[props.field_name];
     f.choices = simManager.getFolders().map((v) => {
         return {
             code: v,
             display: v,
         };
     });
 });
</script>
