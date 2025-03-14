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
            res.html = res.text = function(v) {
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

        function assertTicks(actual, expected, expectedBase) {
            expect(actual).toEqual(expected);
            expect(formattedBase).toEqual(expectedBase || '');
        }

        assertTicks(
            tickValues('', [0.000002, 0.000016], { width: 488, height: 278 }, 'y', 'left'),
            ['2.0e-6', '4.0e-6', '6.0e-6', '8.0e-6', '1.0e-5', '1.2e-5', '1.4e-5', '1.6e-5'],
        );
        assertTicks(
            tickValues('', [0.000002, 0.000016], { width: 488, height: 278 }, 'y', 'left'),
            ['2.0e-6', '4.0e-6', '6.0e-6', '8.0e-6', '1.0e-5', '1.2e-5', '1.4e-5', '1.6e-5'],
        );
        assertTicks(
            tickValues('p (mec)', [1091.8533911592672, 1102.8071108461356], { width: 423, height: 423}, 'y', 'left'),
            ['1092', '1094', '1096', '1098', '1100', '1102'],
        );
        assertTicks(
            tickValues('Particles', [9900, 10000], {width: 423, height: 423}, 'y', 'left'),
            ['9.90e+3', '9.92e+3', '9.94e+3', '9.96e+3', '9.98e+3', '1.00e+4'],
        );
        assertTicks(
            tickValues('Particles', [9950, 10050], {width: 423, height: 423}, 'y', 'left'),
            ['9.960e+3', '9.980e+3', '1.000e+4', '1.002e+4', '1.004e+4'],
        );
        assertTicks(
            tickValues('Particles', [7500, 10000], {width: 423, height: 423}, 'y', 'left'),
            ['7.5e+3', '8.0e+3', '8.5e+3', '9.0e+3', '9.5e+3', '1.0e+4'],
        );
        assertTicks(
            tickValues('t [s]', [1.2281523024139837e-7, 1.2281730720114474e-7], {width: 468, height: 468}, 'x', 'bottom'),
            ['-0.8', '-0.6', '-0.4', '-0.2', '0', '0.2', '0.4', '0.6', '0.8', '1.0'],
            '< t > = 122.8162 ns',
        );
        assertTicks(
            tickValues('', [-0.0005, -0], {width: 497, height: 284}, 'y', 'left'),
            ['-5e-4', '-4e-4', '-3e-4', '-2e-4', '-1e-4', '0'],
        );
        assertTicks(
            tickValues('', [-0.0005, 100], {width: 497, height: 284}, 'y', 'left'),
            ['0', '20', '40', '60', '80', '100'],
        );
        assertTicks(
            tickValues('', [-0.0005, 10000], {width: 497, height: 284}, 'y', 'left'),
            ['0', '2e+3', '4e+3', '6e+3', '8e+3', '1e+4'],
        );
        assertTicks(
            tickValues('', [0, 50000], {width: 497, height: 284}, 'y', 'left'),
            ['0', '1e+4', '2e+4', '3e+4', '4e+4', '5e+4'],
        );
        assertTicks(
            tickValues('', [10000000000000000, 60000000000000000], {width: 653, height: 387}, 'y', 'left'),
            ['1e+16', '2e+16', '3e+16', '4e+16', '5e+16', '6e+16'],
        );
        assertTicks(
            tickValues('', [106.33059406714369, 106.97703902321857], {width: 653, height: 467}, 'y', 'left'),
            ['106.4', '106.5', '106.6', '106.7', '106.8', '106.9'],
        );
        assertTicks(
            tickValues('t [s]', [3.0014645053460535e-8, 3.002773210920325e-8], {width: 633, height: 467}, 'x', 'bottom'),
            ['30.016', '30.018', '30.020', '30.022', '30.024', '30.026'],
        );
        assertTicks(
            tickValues('', [3.0014645053460535e-8, 3.002773210920325e-8], {width: 633, height: 467}, 'x', 'bottom'),
            ['-6e-12', '-4e-12', '-2e-12', '0', '2e-12', '4e-12'],
            '+3.0022e-8',
        );
        assertTicks(
            tickValues('', [-0.0003, 0.0003], {width: 548, height: 313}, 'y', 'left'),
            ['-2e-4', '-1e-4', '0', '1e-4', '2e-4'],
        );
        assertTicks(
            tickValues('', [-0.005903110878804563, 0.0016902793870008444], {width: 493, height: 493}, 'y', 'left'),
            ['-5e-3', '-4e-3', '-3e-3', '-2e-3', '-1e-3', '0', '1e-3'],
        );
        assertTicks(
            tickValues('', [-0.0002, -0.0018], {width: 315, height: 200}, 'y', 'left'),
            ['-1.5e-3', '-1.0e-3', '-5.0e-4'],
        );
        assertTicks(
            tickValues('', [-0.02, 0], {width: 350, height: 180}, 'y', 'left'),
            ['-0.02', '-0.01', '0'],
        );
        assertTicks(
            tickValues('', [0, 0.02], {width: 350, height: 180}, 'y', 'left'),
            ['0', '0.01', '0.02'],
        );
        assertTicks(
            tickValues('', [0.9989999999999999, 1.001], {width: 661, height: 315}, 'y', 'left'),
            ['-1e-3', '-5e-4', '0', '5e-4'],
            '+1',
        );
        assertTicks(
            tickValues('W [eV]', [0.9989999999999999, 1.001], {width: 661, height: 315}, 'y', 'left'),
            ['-1.0', '-0.5', '0', '0.5'],
            '< W > = 1 eV',
        );
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
