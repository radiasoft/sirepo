<template>

    <div class="row">
        <div v-if="root" class="col-sm-4 col-md-3 sr-sidebar">
            <ul class="nav sr-nav-sidebar sr-nav-sidebar-root">
                <VFolderNav :folder="root" :selected_folder="selectedFolder" @folderSelected="folderSelected"/>
            </ul>
        </div>
        <div class="col-sm-8 col-md-9">

            <div v-for="item in items" :key="item.key" class="sr-icon-col">
                <div class="sr-thumbnail text-center dropdown-center">
                    <a href @dblclick="openItem(item)" data-bs-toggle="dropdown" style="padding-bottom: 30px">
                        <span
                            class="sr-item-icon"
                            :class="{
                                'sr-user-item': ! item.isExample,
                                'bi bi-folder2': item.isFolder,
                                'bi bi-file-earmark': ! item.isFolder,
                                'sr-transparent-icon': ! item.isFolder && item.isExample,
                                'sr-transparent-icon-user': ! item.isFolder && ! item.isExample
                            }"></span>
                        <span class="dropdown-toggle"></span>
                    </a>

                    <div>
                        <a href @click.prevent="openItem(item)">
                            <span :class="{
                                'sr-user-item': ! item.isExample
                            }">
                                {{ item.name }}
                            </span>
                        </a> <VTooltip v-if="item.notes" :tooltip="item.notes" />
                    </div>

                    <ul class="dropdown-menu">

                        <li><a href @click.prevent="openItem(item)" class="dropdown-item">
                            <span
                                class="sr-nav-icon"
                                :class="{
                                    'bi bi-folder2-open': item.isFolder,
                                    'bi bi-file-earmark-arrow-up': ! item.isFolder
                                }"></span> Open
                        </a></li>
                        <li v-if="! item.isFolder"><a href @click.prevent="copyItem(item)" class="dropdown-item">
                            <span
                                class="sr-nav-icon bi bi-copy"></span> Open as a New Copy
                        </a></li>
                        <li v-if="! item.isExample"><a href @click.prevent="renameItem(item)" class="dropdown-item">
                            <span
                                class="sr-nav-icon bi bi-pencil-square"></span> Rename
                        </a></li>
                        <li v-if="! item.isExample"><a href @click.prevent="moveItem(item)" class="dropdown-item">
                            <span class="sr-nav-icon bi bi-box-arrow-right"></span> Move
                        </a></li>
                        <li v-if="! item.isFolder"><a :href="exportArchiveUrl(item)" class="dropdown-item">
                            <span class="sr-nav-icon bi bi-save"></span> Export as Zip
                        </a></li>
                        <li v-if="! item.isFolder"><a :href="sourceCodeUrl(item)" class="dropdown-item">
                            <span class="sr-nav-icon bi bi-cloud-download"></span> Source Code
                        </a></li>
                        <li v-if="canDelete(item)" class="dropdown-divider"></li>
                        <li v-if="canDelete(item)"><a href @click.prevent="deleteItem(item)" class="dropdown-item">
                            <span class="bi bi-trash"></span> Delete</a></li>
                    </ul>


                </div>
            </div>


        </div>
    </div>

    <VFormModal viewName="renameItem" title="Rename" ref="renameModal"/>

    <VConfirmationModal
        ref="deleteModal"
        title="Delete Simulation?"
        okText="Delete"
        @okClicked="deleteSelected"
    >
        Delete simulation &quot;{{ selectedItem && selectedItem.name }}&quot;?
    </VConfirmationModal>

    <!--
    <script type="text/ng-template" id="sr-folder">
        <a href data-ng-click="simulations.toggleFolder(item)">
            <span class="glyphicon sr-small-nav-icon" data-ng-class="{'glyphicon-chevron-down': item.isOpen, 'glyphicon-chevron-right': ! item.isOpen}"></span>
            <span class="glyphicon sr-nav-icon" data-ng-class="{'sr-user-item': ! simulations.isRootFolder(item) && ! simulations.fileManager.isFolderExample(item), 'glyphicon-folder-open': item.isOpen, 'glyphicon-folder-close': ! item.isOpen}"></span> <span data-ng-class="{ 'sr-user-item': ! simulations.isRootFolder(item) && ! simulations.fileManager.isFolderExample(item) }">{{ item.name }}</span>
        </a>
        <ul data-ng-if="item.isOpen" class="nav sr-nav-sidebar">
            <li data-ng-repeat="item in item.children | filter:{isFolder: true} | orderBy:'name'" data-ng-include="'sr-folder'" data-ng-class="{'active': simulations.isActiveFolder(item)}"></li>
        </ul>
    </script>

    <div class="container-fluid">
        <div class="row">
            <div class="hidden-xs col-sm-4 col-md-3 sr-sidebar">
                <ul class="nav sr-nav-sidebar sr-nav-sidebar-root">
                    <li data-ng-repeat="item in simulations.fileTree" data-ng-include="'sr-folder'" data-ng-class="{'active': simulations.isActiveFolder(item)}"></li>
                </ul>
            </div>
            <div class="col-sm-8 col-md-9">
                <div class="sr-iconset">
                    <div class="sr-folder-nav visible-xs clearfix">
                        <a href data-ng-repeat="item in simulations.activeFolderPath" data-ng-click="simulations.openItem(item)"><span data-ng-if="simulations.isRootFolder(item)" class="glyphicon glyphicon-folder-open sr-nav-icon"></span><span data-ng-if="! simulations.isRootFolder(item)" class="glyphicon glyphicon-chevron-right sr-small-nav-icon"></span><span data-ng-class="{ 'sr-user-item': ! simulations.fileManager.isFolderExample(item) }">{{ item.name }}</span> </a>
                    </div>
                    <div class="col-sm-12" data-get-started=""></div>
                    <div class="sr-icon-view-toggle"><a href data-ng-click="simulations.toggleIconView()"><span class="glyphicon" data-ng-class="{'glyphicon-th-list': simulations.isIconView, 'glyphicon-th-large': ! simulations.isIconView }"></span> View as {{ simulations.isIconView ? 'List' : 'Icons' }}</a></div>
                    <div class="col-sm-6" data-list-search="simulations.getSimPaths()" data-on-select="simulations.openItem" data-placeholder-text="search"></div>
                    <div class="clearfix"></div>

                    <div style="margin-left: 2em; margin-top: 1ex;" class="lead" data-ng-show="simulations.isWaitingForList"><img src="/static/img/sirepo_animated.gif" /> Building simulation list, please wait.</div>
                    <div data-ng-hide="simulations.isIconView" class="row"><div class="col-sm-offset-1 col-sm-10">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th data-ng-repeat="col in simulations.listColumns"><a data-ng-class="{'dropup': simulations.isSortAscending()}" href data-ng-click="simulations.toggleSort(col.field)">{{ col.heading }} <span data-ng-if="simulations.sortField.indexOf(col.field) >= 0" class="caret"></span></a></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr data-ng-repeat="item in simulations.activeFolder.children | orderBy:['isFolder', simulations.sortField]">
                                    <td><a href data-ng-click="simulations.openItem(item)"><span class="glyphicon" data-ng-class="{'sr-user-item': ! simulations.fileManager.isItemExample(item), 'glyphicon-folder-close': item.isFolder, 'glyphicon-file': ! item.isFolder, 'sr-transparent-icon': ! item.isFolder && item.isExample, 'sr-transparent-icon-user': ! item.isFolder && ! item.isExample}"></span> <span data-ng-class="{ 'sr-user-item': ! simulations.fileManager.isItemExample(item) }">{{ item.name | simulationName }}</span></a> <span data-sr-tooltip="{{ item.notes }}"><span></td>
                                        <td>{{ item.lastModified | date:'medium' }}</td>
                                </tr>
                                <tr data-ng-show="simulations.isWaitingForSim">
                                    <td>
                                        <img src="/static/img/sirepo_animated.gif" width="24px"/>
                                        <a>Creating {{ simulations.newSimName }}...</a>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div></div>

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
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div data-confirmation-modal="" data-id="sr-delete-confirmation" data-title="Delete Simulation?" data-ok-text="Delete" data-ok-clicked="simulations.deleteSelected()">Delete simulation &quot;{{ simulations.selectedItem.name }}&quot;?</div>

    <div data-confirmation-modal="" data-id="sr-rename-confirmation" data-title="Rename {{ simulations.selectedItemType() }}" data-ok-text="Rename" data-ok-clicked="simulations.renameSelected()">
        <form class="form-horizontal" autocomplete="off">
            <label class="col-sm-3 control-label">New Name</label>
            <div class="col-sm-9">
                <input data-safe-path="" class="form-control" data-ng-model="simulations.renameName" required/>
                <div class="sr-input-warning" data-ng-show="showWarning">{{warningText}}</div>
            </div>
        </form>
    </div>


    <div data-copy-confirmation="" data-sim-id="simulations.selectedItem.simulationId" data-copy-cfg="simulations.copyCfg" data-disabled="false">
    </div>

    <div data-confirmation-modal="" data-id="sr-move-confirmation" data-title="Move {{ simulations.selectedItemType() }}" data-ok-text="Move" data-ok-clicked="simulations.moveSelected()">
        <form class="form-horizontal" autocomplete="off">
            <label class="col-sm-3 control-label">New Folder</label>
            <div class="col-sm-9">
                <select class="form-control" data-ng-model="simulations.targetFolder" data-ng-options="folder as simulations.pathName(folder) for folder in simulations.moveFolderList"></select>
            </div>
        </form>
    </div>
-->

</template>

<script setup>
 import VConfirmationModal from '@/components/VConfirmationModal.vue';
 import VFolderNav from '@/components/VFolderNav.vue';
 import VFormModal from '@/components/VFormModal.vue'
 import VTooltip from '@/components/VTooltip.vue';
 import { appState, MODEL_CHANGED_EVENT } from '@/services/appstate.js';
 import { onMounted, onUnmounted, reactive, ref } from 'vue';
 import { pubSub } from '@/services/pubsub.js';
 import { requestSender } from '@/services/requestsender.js';
 import { simManager } from '@/services/simmanager.js';
 import { uri } from '@/services/uri.js';
 import { useRoute, useRouter } from 'vue-router';

 // example: open, open as a new copy, export as zip, python source
 // open, open as a new copy, rename, move, export as zip, python source | delete

 const route = useRoute();
 const router = useRouter();

 const folders = ref([]);
 const items = ref([]);
 const root = ref(null);
 const selectedFolder = ref(null);
 const selectedItem = ref(null);

 const renameModal = ref(null);
 const deleteModal = ref(null);

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

 const renameItem = async (item) => {
     await appState.clearModels({
         renameItem: {
             newName: item.name,
             oldName: item.name,
             isFolder: item.isFolder,
             simulationId: item.simulationId,
         },
     });
     renameModal.value.showModal();
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
     if (item.isFolder) {
         //TODO(pjm): remove folder
     }
     else {
         selectedItem.value = item;
         deleteModal.value.showModal();
     }
 };

 const deleteSelected = async () => {
     await appState.deleteSimulation(selectedItem.value.simulationId);
     selectedItem.value = null;
     deleteModal.value.closeModal();
 };

 const onModelChanged = (names) => {
     if (names[0] === 'renameItem') {
         //TODO(pjm): requestSender call to save
     }
 };

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
     pubSub.subscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

 onUnmounted(() => {
     pubSub.unsubscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

</script>
