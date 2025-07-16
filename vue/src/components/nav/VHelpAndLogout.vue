<template>
    <ul class="navbar-nav">
        <li class="nav-item dropdown">
            <a href class="nav-link dropdown-toggle" data-bs-toggle="dropdown">
                <span class="bi bi-question-circle sr-nav-icon"></span>
                <span class="caret"></span>
            </a>
            <ul class="dropdown-menu dropdown-menu-end">
                <li>
                    <a
                        class="dropdown-item"
                        v-bind:href="'mailto:' + schema.feature_config.support_email"
                    >
                        <span class="bi bi-envelope sr-nav-icon"></span> Contact Support
                    </a>
                </li>
                <li>
                    <a
                        class="dropdown-item"
                        href="https://github.com/radiasoft/sirepo/issues"
                        target="_blank"
                    >
                        <span class="bi bi-exclamation-circle sr-nav-icon"></span> Report a Bug
                    </a>
                </li>
                <!--
                <li data-help-link="helpUserManualURL" data-title="User Manual" data-icon="list-alt"></li>
                <li data-help-link="helpUserForumURL" data-title="User Forum" data-icon="globe"></li>
                -->
            </ul>
        </li>
    </ul>

    <ul v-if="authState.isLoggedIn && ! authState.isGuestUser" class="navbar-nav">
        <li class="nav-item dropdown">
            <a href class="nav-link dropdown-toggle" data-bs-toggle="dropdown">
                <img
                    class="sr-user-avatar"
                    v-if="authState.avatarUrl"
                    v-bind:src="authState.avatarUrl"
                />
                <span v-if="! authState.avatarUrl" class="bi bi-person sr-nav-icon"></span>
                <span class="caret"></span>
            </a>
            <ul class="dropdown-menu dropdown-menu-end">
                <li><span class="dropdown-header">{{ authState.displayName }}</span></li>
                <!--
                <li class="dropdown-header">{{ authState.paymentPlanName() }}</li>
                -->
                <li v-if="authState.userName"><span class="dropdown-header">{{ authState.userName }}</span></li>
                <!--
                <li data-ng-if="isAdm()"><a data-ng-href="{{ getUrl('admJobs') }}">Admin Jobs</a></li>
                <li data-ng-if="isAdm()"><a data-ng-href="{{ getUrl('admUsers') }}">Admin Users</a></li>
                <li><a data-ng-click="showJobsList()" style="cursor:pointer">Jobs</a></li>
                -->
                <li>
                    <a
                        class="dropdown-item"
                        v-bind:href="logoutURL()"
                    >
                        Sign out
                    </a>
                </li>
            </ul>
        </li>
    </ul>
</template>

<script setup>
 import { authState } from '@/services/authstate.js';
 import { schema } from '@/services/schema.js';
 import { uri } from '@/services/uri.js';

 const logoutURL = () => uri.format('authLogout');
</script>
