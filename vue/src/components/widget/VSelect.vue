<!--
   An HTML SELECT element with a list of choices.
 -->
<template>
    <div>
        <select
            v-model="ui_ctx.fields[field_name].val"
            class="form-control form-select form-select-sm"
            v-bind:class="{
                'sr-invalid': error,
            }"
            v-on:input="onInput"
            v-bind:disabled="! enabled"
        >
            <option
                v-for="v of ui_ctx.fields[field_name].choices"
                v-bind:key="v.code"
                v-bind:value="v.code">{{ v.display }}
            </option>
        </select>
        <div v-if="error" class="invalid-feedback">
            {{ error }}
        </div>
    </div>
</template>

<script setup>
 import { useWidget } from '@/components/widget/useWidget.js';

 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });

 const { enabled, error, field, onInput } = useWidget(props.ui_ctx, props.field_name);

</script>
