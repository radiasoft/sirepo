<!--
   A list of available sim folders.
 -->
<template>
    <VSelect
        :field_name="field_name"
        :ui_ctx="ui_ctx"
    />
</template>

<script setup>
 import VSelect from '@/components/widget/VSelect.vue';
 import { appState } from '@/services/appstate.js';
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
