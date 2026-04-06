<template>
    <table class="table table-striped">
        <thead>
            <tr>
                <th
                    v-for="col in cols"
                    v-bind:key="col.name"
                    class="sr-table-heading"
                >
                    <a href v-on:click.prevent="sortCol(col)">
                        {{ col.heading }}
                    </a>&nbsp;<a href v-on:click.prevent="sortCol(col)" class="sr-sort-icon">
                        {{ sortIcon(col) }}
                    </a>
                </th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <tr
                v-for="mat in state.materials"
                v-bind:key="mat.material_id"
            >
                <td
                    v-for="col in cols"
                    v-bind:key="col.name"
                >
                    {{ formatValue(mat, col) }}
                </td>
                <td class="sr-button-bar-td">
                    <div class="sr-button-bar-parent">
                        <div class="sr-button-bar">
                            <VMaterialLink
                                v-bind:materialId="mat.material_id"
                                v-bind:adminView="adminView"
                            >
                                <div class="btn btm-sm btn-info">
                                    View
                                </div>
                            </VMaterialLink>
                            <button
                                v-if="! adminView"
                                type="button"
                                v-on:click="removeMaterial(mat)"
                                class="btn btn-danger btn-sm"
                            >
                                <span class="bi bi-trash3"></span>
                            </button>
                        </div>
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
    <VConfirmationModal
        ref="confirmDeleteModal"
        title="Delete Material"
        okText="Delete"
        v-on:okClicked="deleteSelectedMaterial"
    >
        Delete material <strong>{{ selectedMaterial.material_name }}</strong>?
    </VConfirmationModal>
</template>

<script setup>
 import VConfirmationModal from '@/components/VConfirmationModal.vue';
 import VMaterialLink from '@/apps/cortex/VMaterialLink.vue';
 import { RouterLink } from 'vue-router';
 import { db, DB_UPDATED } from '@/apps/cortex/db.js';
 import { onMounted, onUnmounted, reactive, ref } from 'vue';
 import { pubSub } from '@/services/pubsub.js';
 import { requestSender } from '@/services/requestsender.js';
 import { util } from '@/services/util.js';

 const props = defineProps({
     adminView: Boolean,
 });

 const emit = defineEmits(['materialCount']);
 const confirmDeleteModal = ref(null);
 const selectedMaterial = ref(null);

 const cols = reactive([
     {
         name: 'material_name',
         heading: 'Material Name',
     },
     {
         name: 'created',
         heading: 'Date Uploaded',
         format: (v) => util.formatDate(v),
     },
     {
         name: 'is_public',
         heading: 'Public',
         format: (v) => v ? 'Yes' : 'No',
     },
     {
         name: 'is_plasma_facing',
         heading: 'Material Type',
         format: (v) => v ? 'plasma-facing' : 'structural',
     },
 ]);
 const state = reactive({
     sort: ['material_name', true],
     materials: [],
 });

 const deleteSelectedMaterial = async () => {
     confirmDeleteModal.value.closeModal();
     await db.deleteMaterial(selectedMaterial.value.material_id);
     await requestSender.sendRequest("cortexSim", {
         op_name: 'delete',
         op_args: {
             material_id: selectedMaterial.value.material_id,
         },
     });
     _loadMaterials();
 };

 const formatValue = (material, col) => {
     const v = material[col.name];
     return col.format ? col.format(v) : v;
 };

 const removeMaterial = (material) => {
     selectedMaterial.value = material;
     confirmDeleteModal.value.showModal();
 };

 const sortCol = (col) => {
     if (state.sort[0] === col.name) {
         state.sort[1] = ! state.sort[1];
     }
     else {
         state.sort = [col.name, true];
     }
     _sortMaterials();
 };

 const sortIcon = (col) => {
     if (state.sort[0] === col.name) {
         return state.sort[1] ? '▲' : '▼';
     }
     return '';
 }

 const _loadMaterials = async () => {
     // don't show the import panel until we know how many materials are present
     emit('materialCount', undefined);
     state.materials = await db.listMaterials(props.adminView);

     const c = cols.map((v) => v.name);
     for (const r of state.materials) {
         for (const k in r) {
             if (k !== 'material_id' && k !== 'uid' && ! c.includes(k)) {
                 c.push(k);
                 cols.push({
                     name: k,
                     heading: k,
                     format: (v) => util.formatExponential(v),
                 });
             }
         }
     }
     emit('materialCount', state.materials.length);
     _sortMaterials();
 };

 const _sortMaterials = () => {
     state.materials.sort(
         (a, b) => {
             let v;
             const col = state.sort[0];
             if (typeof a[col] === 'string') {
                 v = a[col].localeCompare(b[col]);
             }
             else if (a[col] === undefined) {
                 return 1;
             }
             else if (b[col] === undefined) {
                 return -1;
             }
             else if (a[col] < b[col]) {
                 v = -1;
             }
             else if (a[col] > b[col]) {
                 v = 1;
             }
             return state.sort[1] ? v : -v;
         },
     );
 };

 onMounted(async () => {
     if (props.adminView) {
         cols.unshift({
             name: 'username',
             heading: 'User Name',
         });
     }
     pubSub.subscribe(DB_UPDATED, _loadMaterials);
     await _loadMaterials();
 });

 onUnmounted(() => {
     pubSub.unsubscribe(DB_UPDATED, _loadMaterials);
 });
</script>

<style scoped>
 .sr-sort-icon {
     display: inline-block;
     min-width: 1em;
 }
 .sr-table-heading {
     vertical-align: top;
 }
</style>
