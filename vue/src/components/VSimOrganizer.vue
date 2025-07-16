<template>

    <div class="row">
        <div v-if="root" class="col-sm-4 col-md-3 sr-sidebar">
            <ul class="nav sr-nav-sidebar sr-nav-sidebar-root">
                <VFolderNav
                    v-bind:folder="root"
                    v-bind:selected_folder="selectedFolder"
                    v-on:folderSelected="folderSelected"
                />
            </ul>
        </div>
        <div class="col-sm-8 col-md-9">

            <div v-for="item in items" v-bind:key="item.key" class="sr-icon-col">
                <div class="sr-thumbnail text-center dropdown-center">
                    <a href v-on:dblclick="openItem(item)" data-bs-toggle="dropdown" style="padding-bottom: 30px">
                        <span
                            class="sr-item-icon"
                            v-bind:class="{
                                'sr-user-item': ! item.isExample,
                                'bi bi-folder2': item.isFolder,
                                'bi bi-file-earmark': ! item.isFolder,
                                'sr-transparent-icon': ! item.isFolder && item.isExample,
                                'sr-transparent-icon-user': ! item.isFolder && ! item.isExample
                            }"></span>
                        <span class="dropdown-toggle"></span>
                    </a>

                    <div>
                        <a href v-on:click.prevent="openItem(item)">
                            <span v-bind:class="{
                                'sr-user-item': ! item.isExample
                            }">
                                {{ item.name }}
                            </span>
                        </a> <VTooltip v-if="item.notes" v-bind:tooltip="item.notes" />
                    </div>

                    <ul class="dropdown-menu">

                        <li><a href v-on:click.prevent="openItem(item)" class="dropdown-item">
                            <span
                                class="sr-nav-icon"
                                v-bind:class="{
                                    'bi bi-folder2-open': item.isFolder,
                                    'bi bi-file-earmark-arrow-up': ! item.isFolder
                                }"></span> Open
                        </a></li>
                        <li v-if="! item.isFolder"><a href v-on:click.prevent="copyItem(item)" class="dropdown-item">
                            <span
                                class="sr-nav-icon bi bi-copy"></span> Open as a New Copy
                        </a></li>
                        <li v-if="! item.isExample"><a href v-on:click.prevent="renameItem(item)" class="dropdown-item">
                            <span
                                class="sr-nav-icon bi bi-pencil-square"></span> Rename
                        </a></li>
                        <li v-if="! item.isExample"><a href v-on:click.prevent="moveItem(item)" class="dropdown-item">
                            <span class="sr-nav-icon bi bi-box-arrow-right"></span> Move
                        </a></li>
                        <li v-if="! item.isFolder"><a v-bind:href="exportArchiveUrl(item)" class="dropdown-item">
                            <span class="sr-nav-icon bi bi-save"></span> Export as Zip
                        </a></li>
                        <li v-if="! item.isFolder"><a v-bind:href="sourceCodeUrl(item)" class="dropdown-item">
                            <span class="sr-nav-icon bi bi-cloud-download"></span> Source Code
                        </a></li>
                        <li v-if="canDelete(item)" class="dropdown-divider"></li>
                        <li v-if="canDelete(item)"><a href v-on:click.prevent="deleteItem(item)" class="dropdown-item">
                            <span class="bi bi-trash"></span> Delete</a></li>
                    </ul>


                </div>
            </div>


        </div>
    </div>

    <VFormModal viewName="renameItem" v-bind:title="itemTitle('Rename')" ref="renameModal"/>
    <VFormModal viewName="moveItem" v-bind:title="itemTitle('Move')" ref="moveModal"/>

    <VConfirmationModal
        ref="deleteModal"
        v-bind:title="'Delete ' + strings.formatKey('simulationDataType') + '?'"
        okText="Delete"
        v-on:okClicked="deleteSelected"
    >
        Delete {{ strings.get('simulationDataType') }} &quot;{{ selectedItem && selectedItem.name }}&quot;?
    </VConfirmationModal>

    <!--
                    <div class="col-sm-12" data-get-started=""></div>
                    <div class="sr-icon-view-toggle"><a href data-ng-click="simulations.toggleIconView()"><span class="glyphicon" data-ng-class="{'glyphicon-th-list': simulations.isIconView, 'glyphicon-th-large': ! simulations.isIconView }"></span> View as {{ simulations.isIconView ? 'List' : 'Icons' }}</a></div>
                    <div class="col-sm-6" data-list-search="simulations.getSimPaths()" data-on-select="simulations.openItem" data-placeholder-text="search"></div>
                    <div class="clearfix"></div>

                    <div data-ng-show="simulations.isIconView" style="margin-right: 65px">
                        <div data-ng-repeat="item in simulations.activeFolder.children | orderBy:['isFolder', 'name']" class="sr-icon-col">
                            <div class="sr-thumbnail text-center dropdown">
                                <a href data-ng-dblclick="simulations.openItem(item)" class="sr-item-icon" data-toggle="dropdown">
                                    <span class="caret" style="visibility: hidden"></span><span class="glyphicon" data-ng-class="{'sr-user-item': ! simulations.fileManager.isItemExample(item), 'glyphicon-folder-close': item.isFolder, 'glyphicon-file': ! item.isFolder, 'sr-transparent-icon': ! item.isFolder && item.isExample, 'sr-transparent-icon-user': ! item.isFolder && ! item.isExample}"></span><span data-ng-if="simulations.fileManager.isItemExample(item)" class="glyphicon glyphicon-star sr-example-item" data-ng-class="{ 'sr-example-folder': item.isFolder, 'sr-example-sim': ! item.isFolder }"></span><span class="caret"></span>
                                </a>
                                <div style="display: inline-block"><a href data-ng-click="simulations.openItem(item)"><span data-ng-class="{ 'sr-user-item': ! simulations.fileManager.isItemExample(item) }">{{ item.name | simulationName | limitTo: 60 }}</span></a> <span data-sr-tooltip="{{ item.notes }}"><span></div>
                                    <ul class="dropdown-menu">
                                        <li><a href data-ng-click="simulations.openItem(item)"><span class="glyphicon sr-nav-icon" data-ng-class="{'glyphicon-folder-open': item.isFolder, 'glyphicon-open-file': ! item.isFolder}"></span> Open</a></li>
                                        <li data-ng-if="! item.isFolder && simulations.canCreateNewSimulation()"><a href data-ng-click="simulations.copyItem(item)"><span class="glyphicon glyphicon-duplicate sr-nav-icon"></span> Open as a New Copy</a></li>
                                        <li data-ng-if="! simulations.fileManager.isItemExample(item)"><a href data-ng-click="simulations.renameItem(item)"><span class="glyphicon glyphicon-edit sr-nav-icon"></span> Rename</a></li>
                                        <li data-ng-if="! simulations.fileManager.isItemExample(item)"><a href data-ng-click="simulations.moveItem(item)"><span class="glyphicon glyphicon-arrow-right sr-nav-icon"></span> Move</a></li>
                                        <li data-ng-if="item.canExport"><a data-ng-href="{{ simulations.exportArchiveUrl(item, 'zip') }}"><span class="glyphicon glyphicon-save-file sr-nav-icon"></span> Export as Zip</a></li>
                                        <li data-ng-if="! item.isFolder && simulations.canDownloadInputFile()"><a data-ng-href="{{ simulations.pythonSourceUrl(item) }}"><span class="glyphicon glyphicon-cloud-download sr-nav-icon"></span> {{ simulations.stringsService.formatKey('simulationSource') }}</a></li>
                                        <li data-ng-if="simulations.canDelete(item)" class="divider"></li>
                                        <li data-ng-if="simulations.canDelete(item)"><a href data-ng-click="simulations.deleteItem(item)"><span class="glyphicon glyphicon-trash"></span> Delete</a></li>
                                    </ul>
                            </div>
                        </div>
                        <div data-ng-if=":: simulations.importText" class="sr-icon-col">
                            <div class="sr-thumbnail text-center">
                                <a href data-ng-click="nav.showImportModal()" class="sr-item-icon"><span class="glyphicon glyphicon-cloud-upload sr-import-item"> </span></a>
                                <a data-ng-click="nav.showImportModal()" class="sr-item-text sr-import-item" href>{{:: simulations.importText }}</a>
                            </div>
                        </div>
                        <div data-ng-show="simulations.isWaitingForSim" class="sr-icon-col">
                            <div class="sr-thumbnail text-center dropdown">
                                <a class="sr-item-icon">
                                    <img src="/static/img/sirepo_animated.gif"/>
                                </a>
                                <a class="sr-item-text">Creating {{ simulations.newSimName }}...</a>
                            </div>
                        </div>
-->

</template>

<script setup>
 import VConfirmationModal from '@/components/VConfirmationModal.vue';
 import VFolderNav from '@/components/nav/VFolderNav.vue';
 import VFormModal from '@/components/VFormModal.vue'
 import VTooltip from '@/components/VTooltip.vue';
 import { appResources } from '@/services/appresources.js';
 import { appState } from '@/services/appstate.js';
 import { onMounted, ref, watch } from 'vue';
 import { requestSender } from '@/services/requestsender.js';
 import { simManager } from '@/services/simmanager.js';
 import { strings } from '@/services/strings.js';
 import { uri } from '@/services/uri.js';
 import { useRoute, useRouter } from 'vue-router';
 import { useSimModal } from '@/components/nav/useSimModal.js';

 // example: open, open as a new copy, export as zip, python source
 // open, open as a new copy, rename, move, export as zip, python source | delete

 const route = useRoute();
 const router = useRouter();
 const items = ref([]);
 const root = ref(null);
 const selectedFolder = ref(null);
 const selectedItem = ref(null);
 const deleteModal = ref(null);

 const itemTitle = (prefix) => {
     if (selectedItem.value) {
         return prefix + ' ' + (
             selectedItem.value.isFolder
                 ? 'Folder'
                 : strings.formatKey('simulationDataType')
             );
     }
 };

 const { modalRef: moveModal, showModal: moveItem } = useSimModal(
     'moveItem',
     (item) => {
         selectedItem.value = item;
         return {
             folder: simManager.getFolderPath(simManager.selectedFolder),
             isFolder: item.isFolder,
             folderItem: item,
             simulationId: item.simulationId,
         };
     },
     (moveItem) => {
         if (moveItem.isFolder) {
         }
         else {
             updateSim(moveItem.simulationId, 'folder', moveItem.folder);
         }
     },
 );

 const { modalRef: renameModal, showModal: renameItem } = useSimModal(
     'renameItem',
     (item) => {
         selectedItem.value = item;
         return {
             newName: item.name,
             oldName: item.name,
             isFolder: item.isFolder,
             simulationId: item.simulationId,
         };
     },
     (renameItem) => {
         if (renameItem.isFolder) {
         }
         else {
             updateSim(renameItem.simulationId, 'name', renameItem.newName);
         }
     },
 );

 const init = () => {
     root.value = simManager.root;
     root.value.isOpen = true;
     if (! selectedFolder.value) {
         const n = simManager.getFolderPathFromRoute(route);
         selectedFolder.value = simManager.openFolder(n);
         simManager.selectedFolder = selectedFolder.value;
         if (! selectedFolder.value) {
             uri.localRedirect('notFound');
             return;
         }
     }
     items.value = selectedFolder.value.children;
 };

 const folderSelected = (f) => {
     if (f === selectedFolder.value && f.isOpen) {
         f.isOpen = false;
     }
     else {
         f.isOpen = true;
     }
     selectedFolder.value = f;
     simManager.selectedFolder = selectedFolder.value;
     items.value = selectedFolder.value.children;
     router.push({
         name: 'simulations',
         params: {
             folderPath: selectedFolder.value.path,
         },
     });
 };

 const exportArchiveUrl = (item) => {
     //TODO(pjm): implement this
     return '/';
 };

 const sourceCodeUrl = (item) => {
     //TODO(pjm): implement this
     return '/';
 };

 const canDelete = (item) => {
     if (item.isFolder) {
         return item.children.length === 0;
     }
     return ! item.isExample;
 };

 const deleteItem = (item) => {
     if (! item.isFolder) {
         selectedItem.value = item;
         deleteModal.value.showModal();
     }
 };

 const deleteSelected = async () => {
     await appState.deleteSimulation(selectedItem.value.simulationId);
     simManager.removeSim(selectedItem.value.simulationId);
     selectedItem.value = null;
     deleteModal.value.closeModal();
 };

 const updateSim = async (simulationId, field, value) => {
     const s = await requestSender.sendRequest(
         'simulationData',
         {
             simulation_id: simulationId,
         });
     s.models.simulation[field] = value;
     await requestSender.sendRequest('saveSimulationData', s);
 };

 /*
 const moveFolder = async (oldPath, newPath) => {
     await requestSender.sendRequest(
         'updateFolder',
         {
             oldName: oldPath,
             newName: self.pathName(self.selectedItem),
         });
 };
 */

 const openItem = (item) => {
     if (item.isFolder) {
         folderSelected(item);
         return;
     }
     uri.localRedirectHome(item.simulationId);
 };

 onMounted(async () => {
     appState.clearModels();
     //TODO(pjm): simManager should keep state and not reload from scratch each visit
     await simManager.loadSims();
     init();
 });

 appResources.registerViewLogic('moveItem', (ctx) => {
     watch(ctx, () => {
         if (appState.models.moveItem.isFolder) {
             // don't allow moving a folder into itself
             const p = simManager.getFolderPath(appState.models.moveItem.folderItem);
             const c = ctx.fields.folder.choices;
             for (let i = c.length - 1; i >= 0; i--) {
                 if (c[i].code.startsWith(p)) {
                     c.splice(i, 1);
                 }
             }
         }
     });
 });

</script>
