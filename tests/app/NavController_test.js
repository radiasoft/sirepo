'use strict';
beforeEach(module('SirepoApp'));

describe('Controller: NavController', function() {
    var isLoaded = false;
    beforeEach(module(function ($provide) {
        $provide.value('appState', {
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

    var $controller;

    beforeEach(inject(function(_$controller_) {
        $controller = _$controller_;
    }));

    it('should have default section/title', inject(function() {
        var controller = $controller('NavController', {});
        expect(controller.sectionTitle()).toBe(null);
        expect(controller.pageTitle()).toBe('SRW - Radiasoft');
    }));

    it('should track the active section', inject(function(activeSection) {
        var section = 'hello';
        var controller = $controller('NavController', {});
        activeSection.setActiveSection(section);
        expect(controller.activeSection()).toBe(section);
    }));

    if('should show the simulation name in title', inject(function(activeSection) {
        isLoaded = true;
        var controller = $controller('NavController', {});
        expect(controller.sectionTitle()).toBe('my simulation');
        expect(controller.pageTitle()).toBe('my simulation - SRW - Radiasoft');
    }));
});
