'use strict';
beforeEach(module('SirepoApp'));

describe('Directive: stringToNumber', function() {
    var $scope, $compile, $sniffer;

    beforeEach(inject(function($injector, _$sniffer_) {
        $scope = $injector.get('$rootScope').$new();
        $compile = $injector.get('$compile');
        $sniffer = _$sniffer_;
    }));

    function changeInputValue(element, value) {
        element.val(value);
        browserTrigger(element, $sniffer.hasEvent('input') ? 'input' : 'change');
    }

    function createDirective(template) {
        return $compile(template || '<form name="f1"><input string-to-number ng-model="data"></form>')($scope);
    }

    it('should throw error if nmModel not defined', function() {
        expect(function() { createDirective('<input string-to-number>'); }).toThrow();
    });
    it('should accept numeric input', function() {
        var element = createDirective().find('input');
        expect($scope.data).toEqual(undefined);
        changeInputValue(element, '11');
        expect($scope.data).not.toEqual('11');
        expect($scope.data).toEqual(11);
        expect($scope.f1.$valid).toBe(true);
    });
    it('should accept exponential notation', function() {
        var element = createDirective().find('input');
        changeInputValue(element, '5e2');
        expect($scope.data).toEqual(500);
        expect($scope.f1.$valid).toBe(true);
    });
    it('should mark form as invalid on non-numeric input', function() {
        var element = createDirective().find('input');
        changeInputValue(element, 'x');
        expect(element.val()).toEqual('x');
        expect($scope.data).toEqual(undefined);
        expect($scope.f1.$valid).toBe(false);
    });
});
