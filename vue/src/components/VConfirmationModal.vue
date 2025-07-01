<template>
    <VModal
        ref="modal"
        :title="title"
        themeColor="warning"
        :canDismiss="canDismiss"
        :size="size"
    >
        <div class="row">
            <div class="col-sm-12">
                <slot></slot>
            </div>
            <div v-if="canDismiss" class="col-sm-12 text-center mt-3">
                <button v-if="okText" @click="okClicked" class="btn btn-outline-secondary sr-button-save-cancel">{{ okText }}</button>
                <button type="button" @click="closeModal" class="btn btn-outline-secondary sr-button-save-cancel">{{ cancelText || 'Cancel' }}</button>
            </div>
        </div>
    </VModal>
</template>

<script setup>
 import VModal from '@/components/VModal.vue'
 import { ref } from 'vue';

 const props = defineProps({
     title: String,
     okText: String,
     cancelText: String,
     canDismiss: {
         type: Boolean,
         default: true,
     },
     // size: lg, md, sm, default
     size: {
         type: String,
         default: 'default'
     },
 });

 const emit = defineEmits(['okClicked']);
 const modal = ref(null);

 const okClicked = () => emit('okClicked');

 const closeModal = () => modal.value.closeModal();

 const showModal = () => modal.value.showModal();

 defineExpose({ closeModal, showModal });
</script>
