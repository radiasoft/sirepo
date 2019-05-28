'use strict';
beforeEach(module('SirepoApp'));

describe('Controller: NavController', function() {
    var isLoaded = false;
    beforeEach(module(function ($provide) {
        $provide.value('appState', {
            clone: function() { return {} },
            isLoaded: function() { return isLoaded },
            models: {
                simulation: {
                    simulationId: '123',
                    name: 'my simulation',
                },
            },
        });
        $provide.value('$route', {
            current: {
                params: {},
            },
        });
    }));

    var createController;

    beforeEach(inject(function($injector) {
        var $rootScope = $injector.get('$rootScope');
        var $controller = $injector.get('$controller');
        createController = function() {
            return $controller('NavController', {'$scope': $rootScope});
        };
    }));

    it('should have default section/title', inject(function() {
        isLoaded = false;
        var controller = createController();
        expect(controller.sectionTitle()).toBe(null);
        expect(controller.pageTitle()).toBe('SRW - RadiaSoft');
    }));

    it('should show the simulation name in title', inject(function(activeSection) {
        isLoaded = true;
        var controller = createController();
        expect(controller.sectionTitle()).toBe('my simulation');
        expect(controller.pageTitle()).toBe('my simulation - SRW - RadiaSoft');
    }));
});
