'use strict';
beforeEach(module('SirepoApp'));

describe('Factory: requestQueue', function() {
    var successCallback;
    var errorCallback;

    beforeEach(module(function ($provide) {
        $provide.value('$http', {
            post: function() {
                var self = {};
                self.success = function(callback) {
                    successCallback = callback;
                    return self;
                }
                self.error = function(callback) {
                    errorCallback = callback;
                    return self;
                }
                return self;
            },
        });
    }));

    it('should execute immediate with an empty queue', inject(function(requestQueue) {
        expect(requestQueue).toBeDefined();
        var requestHandled = false;
        requestQueue.addItem(['x', 'x', function() { requestHandled = true }]);
        expect(requestHandled).toBe(false);
        successCallback({});
        expect(requestHandled).toBe(true);
    }));

    it('should queue the second item', inject(function(requestQueue) {
        var requestHandled = false;
        requestQueue.addItem(['x', 'x', function() {}]);
        requestQueue.addItem(['x2', 'x2', function() { requestHandled = true }]);
        expect(requestHandled).toBe(false);
        successCallback({});
        expect(requestHandled).toBe(false);
        successCallback({});
        expect(requestHandled).toBe(true);
    }));

    it('should ignore stale responses', inject(function(requestQueue, $rootScope) {
        var requestHandled = false;
        requestQueue.addItem(['x', 'x', function() { requestHandled = true }]);
        var callback1 = successCallback;
        $rootScope.$broadcast('clearCache');
        requestQueue.addItem(['x2', 'x2', function() { requestHandled = true }]);
        callback1();
        expect(requestHandled).toBe(false);
        successCallback({});
        expect(requestHandled).toBe(true);
    }));

    it('should call error handler on error', inject(function(requestQueue, $rootScope) {
        var errorHandled = false;
        requestQueue.addItem(['x', 'x', function(success, error) { if (error) errorHandled = true }]);
        successCallback({});
        expect(errorHandled).toBe(false);
        requestQueue.addItem(['x', 'x', function(success, error) { if (error) errorHandled = true }]);
        errorCallback({});
        expect(errorHandled).toBe(true);
    }));

    it('should call error handler on error data', inject(function(requestQueue, $rootScope) {
        var errorHandled = false;
        requestQueue.addItem(['x', 'x', function(success, error) { if (error) errorHandled = true }]);
        successCallback({ error: 'err' });
        expect(errorHandled).toBe(true);
    }));
});
