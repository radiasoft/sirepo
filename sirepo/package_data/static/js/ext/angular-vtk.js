'use strict';

//TODO(pjm): copied and modified from angular-d3.js
angular.module('vtk', [])
    .factory('vtkService', function($document, $q, $timeout) {
        try {
            Symbol('void');
        }
        catch(err) {
            // vtk requires Symbol(), not available in MSIE11
            return {};
        }
        var d = $q.defer();
        function onScriptLoad() {
            // Load client in the browser
            $timeout(function() { d.resolve(window.vtk); });
        }
        // Create a script tag with vtk as the source
        // and call our onScriptLoad callback when it
        // has been loaded
        var scriptTag = $document[0].createElement('script');
        scriptTag.type = 'text/javascript';
        scriptTag.async = true;
        scriptTag.src = '/static/js/ext/vtk.js' + SIREPO.SOURCE_CACHE_KEY;
        scriptTag.onreadystatechange = function () {
            if (this.readyState == 'complete') onScriptLoad();
        };
        scriptTag.onload = onScriptLoad;

        var s = $document[0].getElementsByTagName('body')[0];
        s.appendChild(scriptTag);

        return {
            vtk: function() { return d.promise; }
        };
    });
