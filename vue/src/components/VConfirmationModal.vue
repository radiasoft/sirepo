<template>
    <VModal
        ref="modal"
        :title="title"
        themeColor="warning"
        :canDismiss="canDismiss"
        size="default"
        @modalClosed="modalClosed"
    >
        <slot></slot>
    </VModal>
</template>

<script setup>
 import VModal from '@/components/VModal.vue'
 import { ref } from 'vue';

 const props = defineProps({
     title: String,
     canDismiss: {
         type: Boolean,
         default: true,
     },
 });

 const modal = ref(null);

 //TODO(pjm): maybe export this?
 const closeModal = () => modal.value.closeModal();

 //TODO(pjm): maybe propagate this back?
 const modalClosed = () => {};

 const showModal = () => modal.value.showModal();

 defineExpose({ showModal });
</script>
