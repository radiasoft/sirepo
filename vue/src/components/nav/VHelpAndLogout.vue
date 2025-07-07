<template>
    <ul class="navbar-nav">

        <!--
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

                    <li><a href v-on:click="logout">Sign out</a></li>
                </ul>
            </li>

        </ul>
        -->

        <li class="nav-item">
            <a
                class="nav-link"
                v-if="authState.isLoggedIn && ! authState.guestIsOnlyMethod"
                v-bind:href="logoutURL()"
            >
                Sign out
            </a>
        </li>
    </ul>
</template>

<script setup>
 import { authState } from '@/services/authstate.js';
 import { uri } from '@/services/uri.js';

 //TODO(pjm): add help and user menu options

 const logoutURL = () => {
     return uri.format('authLogout');
 };
</script>
