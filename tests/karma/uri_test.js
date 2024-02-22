'use strict';
beforeEach(module('SirepoApp'));

//NOTE: the karma tests have their own schema definition contained in globals.js
//      which does not necessarily match schema-common.json

describe('Factory: uri', function() {
    it('should format uris', inject(function(uri) {
        expect(uri.format('copySimulation', {})).toBe('/copy-simulation');
        expect(uri.format('pythonSource', {
            simulation_id: 'DzYVF6IH',
            simulation_type: 'srw',
            '<model>': 'beamlineAnimation0',
            '<title>': 'Initial Intensity, 20.5m',
        })).toBe('/python-source/srw/DzYVF6IH/beamlineAnimation0/Initial%20Intensity%2C%2020.5m');
    }));
    it('should format local uris', inject(function(uri) {
        expect(uri.formatLocal('simulationsFolder', {
            ':folderPath?': 'Light Source Facilities:NSLS-II:NSLS-II CHX beamline',
        })).toBe('#/simulations/Light%20Source%20Facilities%3ANSLS-II%3ANSLS-II%20CHX%20beamline');
    }));
    it('should throw exceptions on missing arguments', inject(function(uri) {
        expect(() => uri.formatLocal('httpException', {})).toThrow(
            new Error('param=srExceptionOnly param missing map=local route=httpException'),
        );
    }));
});
