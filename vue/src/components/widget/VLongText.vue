<!--
   An HTML TEXTAREA field.
 -->
<template>
    <div>
        <textarea
            v-model="rawValue"
            type="text"
            autocomplete="off"
            class="form-control form-control-sm"
            rows="4"
            cols="50"
            :class="{
                'sr-invalid': isInvalid || error,
            }"
            :disabled="! enabled"
            :readonly="! enabled"
            @input="onInput"
        />
        <div v-if="error" class="invalid-feedback">
            {{ error }}
        </div>
    </div>
</template>

<script setup>
 import { ref, watch } from 'vue';
 import { useValidation } from '@/components/widget/validation/useValidation.js';
 import { useWidget } from '@/components/widget/useWidget.js';

 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
     defaultCols: Number,
 });

 const { enabled, error, field, onInput } = useWidget(props.ui_ctx, props.field_name);

 const { isInvalid, parsedValue, rawValue } = useValidation(field());

 if (props.defaultCols && ! field().cols) {
     field().cols = props.defaultCols;
     }
 else {
     field().cols = 12;
     field().labelcols = 12;
 }

 //TODO(pjm): could share these watch() calls with VText.vue
 watch(() => field().val, () => {
     if (field().val !== parsedValue.value) {
         rawValue.value = field().val;
     }
 });

 watch(parsedValue, () => {
     field().invalid = isInvalid.value;
     if (! isInvalid.value) {
         field().val = parsedValue.value;
     }
 });

 rawValue.value = field().val;
</script>
