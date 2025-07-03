<template>
  <div class="row">
    <div class="col-sm-6 offset-sm-2">
        <h1>{{ title }}</h1>
        <p v-if="routeName === 'notFound' || routeName === 'noRoute'">
           The requested URL was not found on this server.
        </p>
        <p v-else-if="routeName === 'proxyError'">
            The server is unavailable to process your request. Please try again in a few minutes.
        </p>
        <p v-else-if="routeName === 'contentTooLarge'">
            The requested file is too large to download.
        </p>
        <p v-else-if="routeName === 'forbidden'">
            Your browser does not have permission to this page. If you believe this is in error,
            please send a message to our support team <VSupportEmail />.
        </p>
        <p v-else-if="routeName === 'error'">
            The server could not process your request.
        </p>
        <p v-else-if="routeName === 'planRequired'">
            <VPlansLink>Click here to subscribe.</VPlansLink>
        </p>
        <p v-else-if="routeName === 'moderationPending'">
            Your request to access {{ appName }} has been received. For additional information,
            contact <VSupportEmail />.
        </p>
        <p v-else>
            An unknown error occurred.
        </p>
    </div>
  </div>
</template>

<script setup>
 // Used by error and single message routes
 import VPlansLink from '@/components/VPlansLink.vue';
 import VSupportEmail from '@/components/VSupportEmail.vue';
 import { schema } from '@/services/schema.js';
 import { useRoute } from 'vue-router';

 const appName = schema.appInfo[schema.simulationType].shortName;
 const routeName = useRoute().name;
 const title = {
     contentTooLarge: 'Content Too Large',
     error: 'Server Error',
     forbidden: 'Forbidden',
     moderationPending: 'Moderation Pending',
     noRoute: 'Not Found',
     notFound: 'Not Found',
     planRequired: 'Subscription Required',
     proxyError: 'Proxy Error',
 }[routeName] || 'Unknown Error';
</script>
