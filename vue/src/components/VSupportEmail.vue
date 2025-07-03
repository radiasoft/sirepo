<template>
    <a :href="'mailto:' + supportEmail">{{ supportEmail }}</a>
</template>

<script setup>
 import { schema } from '@/services/schema.js';

 const supportEmail = schema.feature_config.support_email;
</script>
