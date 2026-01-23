<template>
    <button
        class="btn ms-2"
        v-bind:class="{
            active: isSelected(),
            'btn-primary': isSelected(),
            'btn-light': ! isSelected(),
        }"
        v-on:click="onClick">
        {{ label }}
    </button>
</template>

<script setup>
 const props = defineProps({
     active: String,
     section: String,
     label: String,
 });
 const emit = defineEmits(['selected']);

 const isSelected = () => props.active === props.section;

 const onClick = () => {
     emit('selected', props.section);
 };
</script>
