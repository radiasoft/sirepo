<!--
   A form field label.
 -->
<template>
    <div class="text-end">
        <label
            class="col-form-label col-form-label-sm"
            :for="field"
        >
            {{ ui_ctx[field].label }}
        <span v-if="ui_ctx[field].tooltip">
            <VTooltip :tooltip="ui_ctx[field].tooltip" />
        </span>
        </label>
    </div>
</template>

<script setup>
 import VTooltip from '@/components/VTooltip.vue'

 const props = defineProps({
     field: String,
     ui_ctx: Object,
 });
</script>
