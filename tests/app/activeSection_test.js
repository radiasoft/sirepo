'use strict';
beforeEach(module('SRWApp'));

describe('Factory: activeSection', function() {
    var params = {};
    var lastId = null;
    beforeEach(module(function ($provide) {
        $provide.value('$route', {
            current: {
                params: params,
            },
        });
        $provide.value('appState', {
            loadModels: function(id) {
                lastId = id;
            },
        });
    }));

    it('should track the active section', inject(function(activeSection) {
        expect(activeSection).toBeDefined();
        var section = 'hello';
        activeSection.setActiveSection(section);
        expect(activeSection.getActiveSection()).toEqual(section);
        expect(lastId).toBeNull();
    }));

    it('should load a simulation from the route params', inject(function(activeSection) {
        var id = '123';
        params.simulationId = id;
        activeSection.setActiveSection('hello');
        expect(lastId).toEqual(id);
    }));
});
