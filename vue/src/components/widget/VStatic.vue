<!--
   A component which shows a label and read-only value.
 -->
<template>
    <div>
        <input
            v-model="ui_ctx[field].value"
            class="form-control form-control-sm form-control-plaintext"
            :id="field"
        />
    </div>
</template>

<script setup>
 const props = defineProps({
     field: String,
     ui_ctx: Object,
 });
</script>
