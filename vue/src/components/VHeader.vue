<template>
    <nav class="navbar navbar-expand-sm static-top bg-light navbar-light">
        <div class="container-fluid">

            <div class="navbar-brand">
                <a href="/">
                    <img
                        width="40"
                        height="38"
                        xclass="d-inline-block align-text-top"
                        src="/static/img/sirepo.gif"
                        alt="Sirepo"
                    >
                </a>
                <div class="d-inline-block ms-3">{{ appName }}</div>
            </div>

            <ul class="navbar-nav me-auto mb-2 mb-sm-0">
                <li class="nav-item">
                    <RouterLink
                        class="nav-link"
                        :class="{ active: isSimulationList }"
                        :to="{
                             name: 'simulations',
                             params: {
                                 folderPath: folderPath,
                             },
                        }">
                        <span class="bi bi-list-task"></span>
                        Simulations
                    </RouterLink>
                </li>

                <li @if="simName" class="nav-item nav-text">
                    <a class="nav-link" href><span class="glyphicon glyphicon-pencil"></span> <strong>{{ simName }}</strong></a>
                </li>

            </ul>
            <div class="d-flex">

                <!--
                <div style="width: 16px"></div>
                <ul class="nav navbar-nav sr-navbar-right" data-ng-show="isLoaded()">
                    <li data-ng-transclude="appHeaderRightSimLoadedSlot">

                        <app-header-right-sim-loaded>
                            <div data-ng-if="nav.isLoaded()" data-sim-sections="">
                                <li class="sim-section" data-ng-if="hasSourceCommand()" data-ng-class="{active: nav.isActive(\'source\')}"><a data-ng-href="{{ nav.sectionURL(\'source\') }}"><span class="glyphicon glyphicon-flash"></span> Source</a></li>
                                <li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a data-ng-href="{{ nav.sectionURL(\'lattice\') }}"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>
                                <li class="sim-section" data-ng-if="latticeService.hasBeamlines()" data-ng-class="{active: nav.isActive(\'control\')}"><a data-ng-href="{{ nav.sectionURL(\'control\') }}"><span class="glyphicon glyphicon-list-alt"></span> Control</a></li>
                                <li class="sim-section" data-ng-if="hasBeamlinesAndCommands()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a data-ng-href="{{ nav.sectionURL(\'visualization\') }}"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                            </div>
                        </app-header-right-sim-loaded>


                    </li>
                    <li data-ng-if="hasDocumentationUrl()"><a href data-ng-click="openDocumentation()"><span
                                                                                                           class="glyphicon glyphicon-book"></span> Notes</a></li>
                    <li data-settings-menu="nav">
                        <app-settings data-ng-transclude="appSettingsSlot"></app-settings>
                    </li>
                </ul>
                -->

                <!--
                <ul class="nav navbar-nav" data-ng-show="nav.isActive('simulations')">
                    <li data-ng-if="SIREPO.APP_SCHEMA.constants.canCreateNewSimulation" class="sr-new-simulation-item"><a href data-ng-click="showSimulationModal()"><span
                                                                                                                                                                         class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-file"></span>
                        {{ newSimulationLabel() }}</a></li>
                    <li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span
                                                                                                                                     class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>
                    <li data-ng-transclude="appHeaderRightSimListSlot">

                        <app-header-right-sim-list>
                            <ul class="nav navbar-nav sr-navbar-right">
                                <li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                            </ul>
                        </app-header-right-sim-list>

                    </li>
                </ul>
                -->

                <!--
                <ul class="navbar-nav">
                    <li class=dropdown><a href class="dropdown-toggle" data-toggle="dropdown"><span
                                                                                                  class="glyphicon glyphicon-question-sign"></span> <span class="caret"></span></a>
                        <ul class="dropdown-menu">
                            <li><a data-ng-href="mailto:{{:: SIREPO.APP_SCHEMA.feature_config.support_email }}">
                                <span class="glyphicon glyphicon-envelope"></span> Contact Support</a></li>
                            <li><a href="https://github.com/radiasoft/sirepo/issues" target="_blank"><span
                                                                                                         class="glyphicon glyphicon-exclamation-sign"></span> Report a Bug</a></li>
                            <li data-help-link="helpUserManualURL" data-title="User Manual" data-icon="list-alt"></li>
                            <li data-help-link="helpUserForumURL" data-title="User Forum" data-icon="globe"></li>
                            <li data-ng-if="SIREPO.APP_SCHEMA.feature_config.show_video_links" data-help-link="helpVideoURL" data-title="Instructional Video" data-icon="film"></li>
                        </ul>
                    </li>
                </ul>
                -->

                <!-- TODO(pjm): use v-once for static parts -->
                <!--
                <ul v-if="authState.isLoggedIn && ! authState.guestIsOnlyMethod" class="nav-item">
                    <li v-if="! authState.isGuestUser" class="sr-logged-in-menu dropdown">

                        <a href class="dropdown-toggle" data-toggle="dropdown">
                            <img v-if="authState.avatarUrl" data-ng-src="{{ authState.avatarUrl }}">
                            <span v-if="! authState.avatarUrl" class="glyphicon glyphicon-user"></span>
                            <span class="caret"></span>
                        </a>

                        <ul class="dropdown-menu">

                            <li class="dropdown-header"><strong>{{ ::authState.displayName }}</strong></li>
                            <li class="dropdown-header">{{ authState.paymentPlanName() }}</li>
                            <li class="dropdown-header" data-ng-if="::authState.userName">{{ ::authState.userName }}</li>
                            <li data-ng-if="isAdm()"><a data-ng-href="{{ getUrl('admJobs') }}">Admin Jobs</a></li>
                            <li data-ng-if="isAdm()"><a data-ng-href="{{ getUrl('admUsers') }}">Admin Users</a></li>
                            <li><a data-ng-click="showJobsList()" style="cursor:pointer">Jobs</a></li>

                            <li><a href @click="logout">Sign out</a></li>
                        </ul>
                    </li>

                </ul>
                -->

                <ul class="navbar-nav me-auto mb-2 mb-sm-0">
                    <li class="nav-item">
                        <a
                            class="nav-link"
                            v-if="! appState.isLoaded()"
                            href
                            @click.prevent="newSimulation"
                        >
                            <span class="bi bi-file-earmark-plus"></span>
                            New Simulation
                        </a>
                    </li>

                    <li class="nav-item">
                        <a
                            class="nav-link"
                            v-if="authState.isLoggedIn && ! authState.guestIsOnlyMethod"
                            :href="logoutURL()"
                        >
                            Sign out
                        </a>
                    </li>
                </ul>

                <!--
                <app-settings>
                </app-settings>
                -->

            </div>
        </div>
    </nav>
    <VFormModal viewName="simulation" title="New Simulation" ref="newModal">
    </VFormModal>
</template>

<script setup>
 import VFormModal from '@/components/VFormModal.vue'
 import { RouterLink } from 'vue-router';
 import { appState, MODEL_CHANGED_EVENT, MODELS_LOADED_EVENT, MODELS_UNLOADED_EVENT } from '@/services/appstate.js';
 import { authState } from '@/services/authstate.js';
 import { onMounted, onUnmounted, ref } from 'vue';
 import { pubSub } from '@/services/pubsub.js';
 import { requestSender } from '@/services/requestsender.js';
 import { simManager } from '@/services/simmanager.js';
 import { uri } from '@/services/uri.js';

 const newModal = ref(null);
 const folderPath = ref('');
 const isSimulationList = ref(false);
 const simName = ref(null);

 //TODO(pjm): longName vs shortName should be dependent on window width
 const appName = appState.schema.appInfo[appState.simulationType].longName;

 const logoutURL = () => {
     return uri.format('authLogout');
 };

 const newSimulation = () => {
     if (appState.isLoaded()) {
         throw new Error('newSimulation expects an unloaded state');
     }
     appState.clearModels({
         simulation: appState.setModelDefaults({
             folder: simManager.getFolderPath(simManager.selectedFolder),
         }, 'simulation'),
     });
     newModal.value.showModal();
 };

 const onLoaded = () => {
     folderPath.value = simManager.formatFolderPath(appState.models.simulation.folder);
     isSimulationList.value = false;
     simName.value = appState.models.simulation.name;
 };

 const onModelChanged = (names) => {
     if (names[0] === 'simulation') {
         // call newSimulation
         appState.models.simulation.folder = simManager.getFolderPath(simManager.selectedFolder);
         requestSender.sendRequest(
             'newSimulation',
             (response) => {
                 //TODO(pjm): implement response handling
             },
             appState.models.simulation,
         );
         // add sim to simManager
         // call openSim
     }
 };

 const onUnloaded = () => {
     isSimulationList.value = true;
     simName.value = null;
 };

 onMounted(() => {
     pubSub.subscribe(MODELS_LOADED_EVENT, onLoaded);
     pubSub.subscribe(MODELS_UNLOADED_EVENT, onUnloaded);
     pubSub.subscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

 onUnmounted(() => {
     pubSub.unsubscribe(MODELS_LOADED_EVENT, onLoaded);
     pubSub.unsubscribe(MODELS_UNLOADED_EVENT, onUnmounted);
     pubSub.unsubscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });


</script>
