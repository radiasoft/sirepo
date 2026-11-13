'use strict';
beforeEach(module('SirepoApp'));

describe('Service: rpnService', function() {

    it('should format values as strings', inject(function(rpnService) {
        expect(rpnService.valueAsString(undefined)).toBeUndefined();
        expect(rpnService.valueAsString(1.5)).toBe('1.5');
        expect(rpnService.valueAsString(2e9)).toBe('2e+9');
        // rpnCache value for an expression that didn't evaluate
        expect(() => rpnService.valueAsString(null)).not.toThrow();
        // numeric string, e.g. a model field value
        expect(() => rpnService.valueAsString('2e9')).not.toThrow();
    }));
});
