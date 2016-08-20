'use strict';

// code from http://www.ng-newsletter.com/posts/d3-on-angular.html
angular.module('d3', [])
    .factory('d3Service', function($document, $q, $timeout) {
        var d = $q.defer();
        function onScriptLoad() {
            // Load client in the browser
            $timeout(function() { d.resolve(window.d3); });
        }
        // Create a script tag with d3 as the source
        // and call our onScriptLoad callback when it
        // has been loaded
        var scriptTag = $document[0].createElement('script');
        scriptTag.type = 'text/javascript';
        scriptTag.async = true;
        scriptTag.src = '/static/js/ext/d3-3.5.9.min.js';
        scriptTag.onreadystatechange = function () {
            if (this.readyState == 'complete') onScriptLoad();
        };
        scriptTag.onload = onScriptLoad;

        var s = $document[0].getElementsByTagName('body')[0];
        s.appendChild(scriptTag);

        return {
            d3: function() { return d.promise; }
        };
    });
