'use strict';
beforeEach(module('SirepoApp'));

describe('Factory: appState', function() {
    var successCallback;
    var errorCallback;

    beforeEach(module(function ($provide) {
        $provide.value('$http', {
            get: function() {
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

    it('should load and manipulate model data', inject(function(appState, $rootScope) {
        spyOn($rootScope, '$broadcast');
        expect(appState).toBeDefined();
        expect($rootScope.$broadcast).not.toHaveBeenCalledWith('clearCache');
        appState.loadModels('123');
        expect($rootScope.$broadcast).toHaveBeenCalledWith('clearCache');
        expect(appState.isLoaded()).toBe(false);
        expect($rootScope.$broadcast).not.toHaveBeenCalledWith('myReport.changed');
        successCallback({
            models: {
                simulation: {
                    simulationId: '123',
                },
                m1: {
                    f1: 'a',
                    f2: 'b',
                },
                m2: {
                    f3: 'c',
                },
                myReport: {
                    f4: 'd',
                },
            },
        });
        expect($rootScope.$broadcast).toHaveBeenCalledWith('myReport.changed');
        expect(appState.isLoaded()).toBe(true);
        expect(appState.models.m1.f1).toBe('a');
        appState.models.m1.f1 = 'x';
        appState.cancelChanges('m2');
        expect(appState.models.m1.f1).not.toBe('a');
        appState.cancelChanges('m1');
        expect(appState.models.m1.f1).toBe('a');
        appState.models.m1.f1 = 'x';
        expect($rootScope.$broadcast).not.toHaveBeenCalledWith('m1.changed');
        appState.saveChanges('m1');
        expect($rootScope.$broadcast).toHaveBeenCalledWith('m1.changed');
        expect(appState.models.m1.f1).toBe('x');
        appState.cancelChanges('m1');
        expect(appState.models.m1.f1).toBe('x');
    }));

    it('should update a report on model changes', inject(function(appState, $rootScope) {
        appState.loadModels('123');
        successCallback({
            models: {
                m1: {},
                myReport1: {},
                myReport2: {},
            },
        });
        spyOn($rootScope, '$broadcast');
        expect($rootScope.$broadcast).not.toHaveBeenCalledWith('myReport1.changed');
        appState.saveChanges('myReport1');
        expect($rootScope.$broadcast).toHaveBeenCalledWith('myReport1.changed');
        expect($rootScope.$broadcast).not.toHaveBeenCalledWith('myReport2.changed');
        expect($rootScope.$broadcast).not.toHaveBeenCalledWith('m1.changed');
        appState.saveChanges('m1');
        expect($rootScope.$broadcast).toHaveBeenCalledWith('m1.changed');
        expect($rootScope.$broadcast).toHaveBeenCalledWith('myReport2.changed');
    }));

    it('should clone models', inject(function(appState, $rootScope) {
        var v = {a: { b: 1}};
        var v2 = appState.clone(v);
        expect(v.a.b).toBeDefined();
        expect(v.a.b).toEqual(v2.a.b);
        v.a.b = 2;
        expect(v.a.b).not.toEqual(v2.a.b);
    }));
});
