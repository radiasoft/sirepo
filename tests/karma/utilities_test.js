'use strict';
beforeEach(module('SirepoApp'));

describe('utilities', function() {

    it('should format an object as text', inject(function(utilities) {
        expect(utilities.objectToText('value')).toBe('value');
        expect(utilities.objectToText({ abc: [123, 456]})).toBe('  abc:\n    123\n    456');
        expect(utilities.objectToText({ abc: { x: 100, y: 200 }, def: { foo: 300 }})).toBe(
            '  abc:\n    x: 100\n    y: 200\n  def:\n    foo: 300');
    }));

    it('should trim text', inject(function(utilities) {
        const t = 'some text\nline 2\nline 3'
        expect(utilities.trimText(t, 10, 100)).toBe(t);
        expect(utilities.trimText(t, 2, 100)).toBe('some text\nline 2');
        expect(utilities.trimText(t, 10, 13)).toBe('some text\nlin');
    }));

});
