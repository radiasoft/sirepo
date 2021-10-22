'use strict';
beforeEach(module('SirepoApp'));

describe('plotting: plotAxis', function() {
    it('should format ticks', inject(function(layoutService) {
        var formattedBase = '';
        var margin = { top: 50, right: 10, bottom: 50, left: 75 };
        var utilitiesStub = {
            debounce: function() {},
        }
        function refreshStub() {
        }
        function selectStub() {
            var res = function() {};
            res.text = function(v) {
                formattedBase = v;
            };
            return res;
        }

        function tickValues(label, domain, canvasSize, dimension, orientation) {
            var axis = layoutService.plotAxis(margin, dimension, orientation, refreshStub, utilitiesStub);
            axis.parseLabelAndUnits(label);
            axis.init();
            axis.scale.domain(domain);
            axis.updateLabelAndTicks(canvasSize, selectStub);
            return axis.scale.ticks(axis.svgAxis.ticks()).map(
                function(v) {
                    return axis.svgAxis.tickFormat()(v);
                });
        }
        var values = tickValues('', [0.000002, 0.000016], { width: 488, height: 278 }, 'y', 'left');
        expect(values).toEqual(['2.0e-6', '4.0e-6', '6.0e-6', '8.0e-6', '1.0e-5', '1.2e-5', '1.4e-5', '1.6e-5']);

        values = tickValues('p (mec)', [1091.8533911592672, 1102.8071108461356], { width: 423, height: 423}, 'y', 'left');
        expect(values).toEqual(['1092', '1094', '1096', '1098', '1100', '1102']);

        values = tickValues('t [s]', [1.2281523024139837e-7, 1.2281730720114474e-7], {width: 468, height: 468}, 'x', 'bottom');
        expect(values).toEqual(['-0.8', '-0.6', '-0.4', '-0.2', '0', '0.2', '0.4', '0.6', '0.8', '1.0']);
        expect(formattedBase).toEqual('< t > = 122.8162ns');

        values = tickValues('', [-0.0005, -0], {width: 497, height: 284}, 'y', 'left');
        expect(values).toEqual(['-5e-4', '-4e-4', '-3e-4', '-2e-4', '-1e-4', '0']);
    }));
    it('should format units', inject(function(layoutService) {
        expect(layoutService.formatUnits('m')).toEqual('[m]');
        expect(layoutService.formatUnits('m', true)).toEqual('(m)');
    }));
    it('should parse units', inject(function(layoutService) {
        expect(layoutService.parseLabelAndUnits('x [m]')).toEqual({
            label: 'x',
            units: 'm',
        });
        expect(layoutService.parseLabelAndUnits('x (m)', true)).toEqual({
            label: 'x',
            units: 'm',
        });
    }));
});
