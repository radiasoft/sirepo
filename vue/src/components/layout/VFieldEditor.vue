<!--
   Field editor based on ui_ctx field widget.
 -->
<template>
    <div class="mb-3">
        <div v-if="widgetComponent">
            <component
                :is="widgetComponent"
                :field_name="field_name"
                :ui_ctx="ui_ctx"
            ></component>
        </div>
        <div v-else-if="isEnum(widgetName)">
            <VEnum
                :field_name="field_name"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div v-else-if="widgetName === 'String'">
            <VText
                :field_name="field_name"
                :ui_ctx="ui_ctx"
                :validation="useValidation"
            />
        </div>
        <div v-else-if="widgetName === 'Email'">
            <VText
                :field_name="field_name"
                :ui_ctx="ui_ctx"
                :validation="useEmailValidation"
            />
        </div>
        <div v-else-if="widgetName === 'Integer'">
            <VText
                class="text-end"
                :field_name="field_name"
                :ui_ctx="ui_ctx"
                :validation="useNumberValidation"
                :defaultCols="3"
            />
        </div>
        <div v-else-if="widgetName === 'Float'">
            <VText
                class="text-end"
                :field_name="field_name"
                :ui_ctx="ui_ctx"
                :validation="useNumberValidation"
                :formatter="formatExponential"
                :defaultCols="3"
            />
        </div>
        <div v-else-if="widgetName === 'UserFolder'">
            <VFolders
                :field_name="field_name"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div v-else-if="['SafePath', 'SimulationName'].includes(widgetName)">
            <VText
                :field_name="field_name"
                :ui_ctx="ui_ctx"
                :validation="usePathValidation"
            />
        </div>
        <div v-else-if="widgetName === 'LongText'">
            <VLongText
                :field_name="field_name"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div v-else-if="widgetName === 'Text'">
            <VLongText
                :field_name="field_name"
                :ui_ctx="ui_ctx"
                :defaultCols="7"
            />
        </div>
        <div v-else>
            Unknown widget type {{ widgetName }}
        </div>
    </div>
</template>

<script setup>
 import VEnum from '@/components/widget/VEnum.vue';
 import VLongText from '@/components/widget/VLongText.vue';
 import VFolders from '@/components/widget/VFolders.vue';
 import VSelect from '@/components/widget/VSelect.vue';
 import VStatic from '@/components/widget/VStatic.vue';
 import VText from '@/components/widget/VText.vue';
 import { appState } from '@/services/appstate.js';
 import { useEmailValidation } from '@/components/widget/validation/useEmailValidation.js';
 import { useNumberValidation } from '@/components/widget/validation/useNumberValidation.js';
 import { usePathValidation } from '@/components/widget/validation/usePathValidation.js';
 import { useValidation } from '@/components/widget/validation/useValidation.js';

 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });

 const getWidgetName = () => {
     let n = props.ui_ctx.fields[props.field_name].widget;
     const w = appState.getWidget(n);
     if (! w && n.startsWith('Optional')) {
         n = n.replace('Optional', '');
         props.ui_ctx.fields[props.field_name].optional = true;
     }
     return [n, w];
 };

 const [widgetName, widgetComponent] = getWidgetName();

 const isEnum = (widgetName) => appState.schema.enum[widgetName] ? true : false;

 //TODO(pjm): move to a utility
 const formatExponential = (value) => {
     if (Math.abs(value) >= 10000 || (value != 0 && Math.abs(value) < 0.001)) {
         value = (+value).toExponential(9).replace(/\.?0+e/, 'e');
     }
     return value;
 };

</script>
