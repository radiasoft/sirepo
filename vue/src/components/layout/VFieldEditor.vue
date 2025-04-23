<!--
   Field editor based on ui_ctx field widget.
 -->
<template>
    <div
        class="mb-3"
        v-if="ui_ctx[name].visible">
        <div v-if="ui_ctx[name].widget == 'select'">
            <VSelect
                :field="name"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div v-else-if="['text', 'float', 'integer'].includes(ui_ctx[name].widget)">
            <VText
                :field="name"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div v-else-if="ui_ctx[name].widget == 'static'">
            <VStatic
                :field="name"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div v-else-if="ui_ctx[name].widget == 'button'">
            <VButton
                :field="name"
                :ui_ctx="ui_ctx"
            />
        </div>
    </div>
</template>

<script setup>
 //TODO(pjm): move VLabel here, remove from widgets
 import VButton from '@/components/widget/VButton.vue';
 import VSelect from '@/components/widget/VSelect.vue';
 import VStatic from '@/components/widget/VStatic.vue';
 import VText from '@/components/widget/VText.vue';

 const props = defineProps({
     name: String,
     ui_ctx: Object,
 });
</script>
