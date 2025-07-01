<template>
    <div class="navbar-brand">
        <a href="/">
            <img
                width="40"
                height="38"
                src="/static/img/sirepo.gif"
                alt="Sirepo"
            >
        </a>
        <div class="d-inline-block ms-3">{{ appName }}</div>
    </div>
</template>

<script setup>
 import { schema } from '@/services/schema.js';
 //TODO(pjm): longName vs shortName should be dependent on window width
 const appName = schema.appInfo[schema.simulationType].longName;
</script>
