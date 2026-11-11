<template>
    <table class="table table-striped">
        <thead>
            <tr>
                <th
                    v-for="col in cols"
                    v-bind:key="col.name"
                    class="sr-table-heading"
                    v-bind:class="{ 'text-end': col.std || col.numeric }"
                >
                    <a href v-on:click.prevent="sortCol(col)">
                        {{ col.heading }}
                    </a>&nbsp;<a href v-on:click.prevent="sortCol(col)" class="sr-sort-icon">
                        {{ sortIcon(col) }}
                    </a>
                    <div v-if="col.subheading" class="sr-subheading">{{ col.subheading }}</div>
                </th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <tr
                v-for="mat in pageItems"
                v-bind:key="mat.material_id"
            >
                <td
                    v-for="col in cols"
                    v-bind:key="col.name"
                    v-bind:class="{ 'text-end': col.std || col.numeric }"
                >{{ formatValue(mat, col) }}<span
                    v-if="col.std && mat[col.name]"
                    class="sr-subheading"
                >&nbsp;&plusmn;&nbsp;{{ formatStd(mat, col) }}</span></td>
                <td class="sr-button-bar-td">
                    <div class="sr-button-bar-parent">
                        <div class="sr-button-bar">
                            <VMaterialLink
                                v-bind:materialId="mat.material_id"
                                >
                                <div class="btn btm-sm btn-info">
                                    View
                                </div>
                            </VMaterialLink>
                            <button
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
            <tr v-if="! visible.length">
                <td v-bind:colspan="cols.length + 1" class="text-muted">
                    No materials match the filter
                </td>
            </tr>
        </tbody>
    </table>
    <VPager
        v-model:page="page"
        v-bind:pageCount="pageCount"
        v-bind:range="pageRange"
        v-bind:total="visible.length"
    />
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
 import VPager from '@/apps/cortex/VPager.vue';
 import { RouterLink } from 'vue-router';
 import { db, DB_UPDATED } from '@/apps/cortex/db.js';
 import { onMounted, onUnmounted, reactive, ref, toRef, watch } from 'vue';
 import { pubSub } from '@/services/pubsub.js';
 import { requestSender } from '@/services/requestsender.js';
 import { util } from '@/services/util.js';
 import { SUMMARY_COLUMNS, useSummary } from '@/apps/cortex/useSummary.js';
 import { usePagedList } from '@/apps/cortex/usePagedList.js';

 const props = defineProps({
     // text to filter by, entered in the header of the card
     filter: { type: String, default: '' },
     // simulation of the summary columns
     report: { type: String, required: true },
 });
 const emit = defineEmits(['materialCount']);
 // a user's materials have wide rows, a user has fewer than the admin batch page
 const PAGE_SIZE = 25;
 const confirmDeleteModal = ref(null);
 const selectedMaterial = ref(null);
 const { formatValue, formatStd } = useSummary();

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
         format: (v) => _typeName(v),
     },
     ...SUMMARY_COLUMNS,
 ]);
 let loadCount = 0;
 const state = reactive({
     sort: ['material_name', true],
     materials: [],
 });
 // the page can be changed outside of the table, which also needs the page count
 const page = defineModel('page', { type: Number, default: 1 });
 const lastPage = defineModel('pageCount', { type: Number, default: 1 });
 const { pageCount, pageItems, pageRange, visible } = usePagedList(
     toRef(state, 'materials'),
     (m, f) => m.material_name.toLowerCase().includes(f) || _type(m).includes(f),
     { filter: toRef(props, 'filter'), page, pageSize: PAGE_SIZE },
 );

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
     // don't show the import panel until we know how many materials are present.
     // Not on a reload, which would hide this table until the list returns, and
     // the page would lose its scroll position.
     if (! state.materials.length) {
         emit('materialCount', undefined);
     }
     const n = ++loadCount;
     const m = await db.listMaterials(props.report);
     if (n !== loadCount) {
         // a newer load was started while waiting
         return;
     }
     state.materials = m;

     const c = cols.map((v) => v.name);
     for (const r of state.materials) {
         for (const k in r) {
             if (k === 'material_id' || k.endsWith('_std') || c.includes(k)) {
                 continue;
             }
             c.push(k);
             cols.push({
                 name: k,
                 heading: k,
                 format: (v) => util.formatExponential(v),
                 numeric: true,
             });
         }
     }
     emit('materialCount', state.materials.length);
     _sortMaterials();
 };

 const _type = (material) => _typeName(material.is_plasma_facing);

 const _typeName = (isPlasmaFacing) => isPlasmaFacing ? 'plasma-facing' : 'structural';

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

 watch(pageCount, (n) => {
     lastPage.value = n;
 }, { immediate: true });

 // the summary columns of another simulation
 watch(() => props.report, _loadMaterials);

 onMounted(async () => {
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
