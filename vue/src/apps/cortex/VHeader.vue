
<template>
    <VNavHolder>
        <VBrand />
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarSupportedContent">
        <ul class="navbar-nav">
            <li class="nav-item">
                <RouterLink
                    class="nav-link"
                    v-bind:class="{ active: isSearch() }"
                    v-bind:to="{ name: 'search' }"
                >
                    <span class="bi bi-list-task sr-nav-icon"></span>
                    Materials
                </RouterLink>
            </li>
        </ul>
        <div class="navbar-nav ms-auto"></div>
        <div v-if="authState.hasRole('adm')" class="float-end">
            <RouterLink to="/cortex/admin">
                <button
                    type="button"
                    class="btn btn-default"
                    v-bind:class="{'btn-warning': isAdmin()}"
                >
                    Admin
                </button>
            </RouterLink>
        </div>
        <VHelpAndLogout />
        </div>
    </VNavHolder>
</template>

<script setup>
 import VBrand from '@/components/nav/VBrand.vue';
 import VHelpAndLogout from '@/components/nav/VHelpAndLogout.vue';
 import VNavHolder from '@/components/nav/VNavHolder.vue';
 import VSimNav from '@/components/nav/VSimNav.vue';
 import { RouterLink } from 'vue-router';
 import { authState } from '@/services/authstate.js';
 import { useRoute } from 'vue-router';

 const route = useRoute();
 const isAdmin = () => ['admin', 'admin-view'].includes(route.name);
 const isSearch = () => route.name === 'search';
</script>
