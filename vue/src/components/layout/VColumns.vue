<!--
   A series of layout components arranged within a bootstrap column class.
   Attributes are:
     - columns: a group of column definitions:
       - layout: the col-* class
       - rows: a group of layout definitions
 -->
<template>
    <div class="row">
        <div
            v-for="(col, index) of columns"
            :key="index"
            :class="'col-' + col.layout">
            <div
                v-for="(row, index2) of col.rows"
                :key="index2">
                <VLayout
                    :layout="row"
                    :ui_ctx="ui_ctx"
                />
            </div>
        </div>
    </div>
</template>

<script setup>
 import VLayout from '@/components/VLayout.vue';

 const props = defineProps({
     columns: Object,
     ui_ctx: Object,
 });
</script>
