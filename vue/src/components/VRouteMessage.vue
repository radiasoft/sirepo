<template>
  <div class="row">
    <div class="col-sm-6 offset-sm-2">
        <h1>{{ title }}</h1>
        <p>{{ message }}</p>
    </div>
  </div>
</template>

<script setup>
 // Used by error and single message routes
 import { ref } from 'vue';
 import { useRoute } from 'vue-router';

 const route = useRoute();

 //TODO(pjm): implement this switching the message depending on the current route name and params
 //TODO(pjm): should be changed to a template switch statement which supports sub elements
 const [title, message] = {
     notFound: [
         'Not Found',
         'The requested URL was not found on this server.',
     ],
     proxyError: [
         'Proxy Error',
         'The server is unavailable to process your request. Please try again in a few minutes.',
     ],
     contentTooLarge: [
         'Content Too Large',
         'The requested file is too large to download.',
     ],
     forbidden: [
         'Forbidden',
         'Your browser does not have permission to this page. If you believe this is in error, please send a message to our support team <span data-support-email=""></span>.',
     ],
     error: [
         'Server Error',
         'The server could not process your request.',
     ],
     planRequired: [
         'Subscription Required',
         '<span data-plans-link="" link-text="Click here to subscribe."></span>',
     ],
     moderationPending: [
         'Moderation Pending',
         'Your request to access {{ appName }} has been received. For additional information, contact <span data-support-email=""></span>.',
     ],
 }[route.name];

</script>
