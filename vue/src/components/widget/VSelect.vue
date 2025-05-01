<!--
   An HTML SELECT element with a list of choices.
 -->
<template>
    <div>
        <select
            v-model="ui_ctx[field_name].val"
            class="form-select form-select-sm"
            @change="onChange()"
        >
            <option
                v-for="v of ui_ctx[field_name].choices"
                :key="v.code"
                :value="v.code">{{ v.display }}
            </option>
        </select>
    </div>
</template>

<script setup>
 import { watch } from 'vue';
 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });

 const onChange = () => {
     props.ui_ctx[props.field_name].isDirty = true;
 };
</script>
