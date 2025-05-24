<!--
   A component which shows a label and read-only value.
 -->
<template>
    <div>
        <input
            v-model="ui_ctx.fields[field_name].val"
            type="text"
            readonly
            class="form-control-sm form-control-plaintext"
        />
    </div>
</template>

<script setup>
 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });
</script>
