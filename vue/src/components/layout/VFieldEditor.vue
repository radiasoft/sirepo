<!--
   Field editor based on ui_ctx field widget.
 -->
<template>
    <div
        class="mb-3"
        v-if="ui_ctx[field_name].visible">
        <div v-if="ui_ctx[field_name].widget == 'select'">
            <VSelect
                :field_name="field_name"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div v-else-if="['text', 'float', 'integer'].includes(ui_ctx[field_name].widget)">
            <VText
                :field_name="field_name"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div v-else-if="ui_ctx[field_name].widget == 'static'">
            <VStatic
                :field_name="field_name"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div v-else>
            Unknown widget type {{ ui_ctx[field_name].widget }}
        </div>
    </div>
</template>

<script setup>
 import VSelect from '@/components/widget/VSelect.vue';
 import VStatic from '@/components/widget/VStatic.vue';
 import VText from '@/components/widget/VText.vue';

 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });
</script>
