<!--
   An HTML SELECT element with a list of choices.
 -->
<template>
    <div>
        <select
            v-model="ui_ctx[field_name].val"
            class="form-select form-select-sm"
            :class="{
                'sr-invalid': error,
            }"
            @change="onChange()"
            :disabled="! enabled"
        >
            <option
                v-for="v of ui_ctx[field_name].choices"
                :key="v.code"
                :value="v.code">{{ v.display }}
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

 const { enabled, error, field } = useWidget(props.ui_ctx, props.field_name);

 const onChange = () => {
     field().isDirty = true;
 };
</script>
