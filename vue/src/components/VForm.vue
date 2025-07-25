<template>
    <form v-on:submit.prevent autocomplete="off" novalidate>
        <div class="row" v-for="f of layout">
            <VLabelAndField
                v-bind:field_name="f"
                v-bind:ui_ctx="ui_ctx"
            />
        </div>
        <slot></slot>
        <div class="row" v-show="showButtons()">
            <div class="col-sm-12 text-center">
                <button
                    class="btn btn-primary sr-button-save-cancel"
                    v-bind:disabled="isInvalid()"
                    v-on:click="saveChanges"
                >
                    {{ strings.saveButtonLabel(props.viewName) }}
                </button>
                <button
                    type="button"
                    class="btn btn-outline-secondary sr-button-save-cancel"
                    v-on:click="cancelChanges"
                >
                    Cancel
                </button>
            </div>
        </div>
    </form>
</template>

<script setup>
 import VLabelAndField from '@/components/layout/VLabelAndField.vue'
 import { appResources } from '@/services/appresources.js';
 import { appState } from '@/services/appstate.js';
 import { reactive } from 'vue';
 import { strings } from '@/services/strings.js';
 import { useModelChanged } from '@/components/useModelChanged.js';

 const props = defineProps({
     viewName: String,
     fieldDef: String,
     wantButtons: {
         type: Boolean,
         default: true,
     },
 });

 const emit = defineEmits(['dismissModal']);

 const ui_ctx = reactive(appState.getUIContext(props.viewName, props.fieldDef));

 //TODO(pjm): view layout may be complicated with columns and tabs
 const layout = ui_ctx.viewSchema[ui_ctx.fieldDef];

 const cancelChanges = () => {
     ui_ctx.cancelChanges(ui_ctx);
     emit('dismissModal');
 };

 const isInvalid = () => ui_ctx.isInvalid();

 useModelChanged((names) => {
     //TODO(pjm): only call if named models are used by UIContext
     cancelChanges();
 });

 const saveChanges = async () => {
     await ui_ctx.saveChanges();
     emit('dismissModal');
 };

 const showButtons = () => props.wantButtons && ui_ctx.isDirty();

 appResources.initViewLogic(props.viewName, ui_ctx);

 defineExpose({ cancelChanges });
</script>
