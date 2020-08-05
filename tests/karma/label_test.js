'use strict';
beforeEach(module('SirepoApp'));

describe('Directive: labelWithTooltip', function() {
    var $scope, $compile;

    beforeEach(inject(function($injector) {
        $scope = $injector.get('$rootScope').$new();
        $compile = $injector.get('$compile');
    }));

    function createDirective(template) {
        return $compile(template)($scope);
    }

    it('should format tooltips with expressions', function() {
        var label = createDirective(angular.element('<div><div data-label-with-tooltip="" data-label="Label Text" data-tooltip="Tooltip Text {{ 1 + 2 }}"></div></div>'));
        $scope.$digest();
        expect(label.html()).toContain('Label Text');
        expect(label.html()).toContain('Tooltip Text 3');
    });

    it('should format math', function() {
        var label = createDirective(angular.element('<div><div data-label-with-tooltip="" data-label="$\\alpha RM$"></div></div>'));
        $scope.$digest();
        expect(label.html()).toContain('α');
    });
});
