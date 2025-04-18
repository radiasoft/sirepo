<script setup>
 defineProps({
     title: String,
     height: Number,
 })
</script>

<template>
    <div class="card mb-4">
        <div class="card-header">{{ title }}</div>
        <div class="card-text">
            <div class="container">
                <div class="text-center"
                     :style="{lineHeight: height + 'px'}">
                    <slot></slot>
                </div>
            </div>
        </div>
    </div>
</template>
