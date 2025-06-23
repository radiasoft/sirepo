<template>
    <VModal
        ref="modal"
        :title="title"
        themeColor="warning"
        :canDismiss="canDismiss"
        size="default"
    >
        <div class="row">
            <div class="col-sm-12">
                <slot></slot>
            </div>
            <div v-if="canDismiss" class="col-sm-12 text-center" style="margin-top: 1em">
                <button v-if="okText" @click="okClicked" class="btn btn-outline-secondary sr-button-save-cancel">{{ okText }}</button>
                <button type="button" @click="closeModal" class="btn btn-outline-secondary sr-button-save-cancel">{{ cancelText || 'Cancel' }}</button>
            </div>
        </div>
    </VModal>
</template>

<script setup>
 import VModal from '@/components/VModal.vue'
 import { defineEmits, ref } from 'vue';

 const props = defineProps({
     title: String,
     okText: String,
     cancelText: String,
     canDismiss: {
         type: Boolean,
         default: true,
     },
 });

 const emit = defineEmits(['okClicked']);
 const modal = ref(null);

 const okClicked = () => emit('okClicked');

 const closeModal = () => modal.value.closeModal();

 const showModal = () => modal.value.showModal();

 defineExpose({ closeModal, showModal });
</script>
