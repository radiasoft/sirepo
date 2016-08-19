'use strict';

// https://solidfoundationwebdev.com/blog/posts/how-to-use-underscore-in-your-angularjs-controllers
angular.module('underscore', [])
    .factory('_', function($window) {return $window._});
