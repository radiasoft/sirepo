<template>
    <VModal ref="modal" :title="title" @modalClosed="modalClosed">
        <VForm :viewName="viewName" fieldDef="advanced" ref="form" @dismissModal="closeModal"/>
    </VModal>
</template>

<script setup>
 import VModal from '@/components/VModal.vue'
 import VForm from '@/components/VForm.vue'
 import { nextTick, ref } from 'vue';

 const props = defineProps({
     title: String,
     viewName: String,
 });

 const form = ref(null);
 const modal = ref(null);

 const closeModal = () => modal.value.closeModal();

 const modalClosed = () => form.value.cancelChanges();

 const showModal = () => modal.value.showModal();

 defineExpose({ showModal });
</script>
