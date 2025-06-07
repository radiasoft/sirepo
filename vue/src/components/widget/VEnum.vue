<!--
   A Sirepo Enum which gets values from the schema.
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

 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });

 const f = props.ui_ctx.fields[props.field_name];
 f.choices = appState.schema.enum[f.widget].map((v) => {
     return {
         code: v[0],
         display: v[1],
     };
 });
</script>
