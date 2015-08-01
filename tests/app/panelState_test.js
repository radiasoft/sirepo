'use strict';
beforeEach(module('SRWApp'));

describe('Factory: panelState', function() {
    var successCallback;
    var errorCallback;

    beforeEach(module(function ($provide) {
        $provide.value('appState', {
            isLoaded: function() { return true; },
            applicationState: function() { return {} },
            isReportModelName: function() { return false },
        });
        //TODO(pjm): share mock objects among other tests
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

    it('should tracking loading/error state', inject(function(panelState) {
        expect(panelState).toBeDefined();
        expect(panelState.isLoading('myReport')).toBe(false);
        expect(panelState.getError('myReport')).toBeNull();
        expect(panelState.isHidden('myReport')).toBe(false);
        panelState.requestData('myReport', function () {});
        expect(panelState.isLoading('myReport')).toBe(true);
        successCallback({ error: 'err' });
        expect(panelState.isLoading('myReport')).toBe(false);
        expect(panelState.getError('myReport')).toBe('err');

        panelState.requestData('myReport', function () {});
        expect(panelState.isLoading('myReport')).toBe(true);
        expect(panelState.getError('myReport')).toBeNull();
        successCallback({});
        expect(panelState.isLoading('myReport')).toBe(false);
        expect(panelState.getError('myReport')).toBeNull();
    }));

    it('should track hidden state', inject(function(panelState) {
        expect(panelState.isHidden('m')).toBe(false);
        panelState.toggleHidden('m');
        expect(panelState.isHidden('m')).toBe(true);
        panelState.toggleHidden('m');
        expect(panelState.isHidden('m')).toBe(false);
    }));

    it('should cache report data', inject(function(panelState) {
        var data = null;
        panelState.requestData('myReport', function(d) { data = d; });
        successCallback({ a: 1 });
        expect(data.a).toEqual(1);
        var originalData = data;
        panelState.requestData('myReport', function(d) { data = d; });
        // this callback doesn't matter, the requestData would return immediately with cached data
        successCallback({ a: 2});
        expect(data.a === originalData.a).toBe(true);
        panelState.clear();
        panelState.requestData('myReport', function(d) { data = d; });
        successCallback({ a: 2});
        expect(data.a).toEqual(2);
    }));
});
