'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.directive('impactxSourceTab', function() {
    return {
        restrict: 'A',
        scope: {
            "source": "<",
        },
        template: `
            <div class="container-fluid">
              <div class="row">
                <div class="col-md-6 col-xl-4">
                  <div data-basic-editor-panel="" data-view-name="distribution"></div>
                </div>
                <div class="col-md-12 col-xl-8">
                  <div class="row">
                    <div data-ng-repeat="item in source.bunchReports track by item.id">
                      <div class="col-md-6">
                        <div data-report-panel="heatmap" data-model-name="bunchReport" data-model-data="item" data-panel-title="{{ source.bunchReportHeading(item) }}"></div>
                      </div>
                      <div data-ng-if="$index % 2" class="clearfix"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div data-modal-editor="" view-name="bunchReport" data-ng-repeat="item in source.bunchReports track by item.id" data-parent-controller="source" data-model-data="item"></div>
        `,
    };
});

SIREPO.viewLogic('distributionView', function(appState, panelState, $scope) {

    function isSDDS() {
        return (appState.models.distribution.distributionFile || '').search(/\.sdds$/i) > 0;
    }

    function updateFields() {
        const d = appState.models.distribution;
        panelState.showFields('distribution', [
            ['k', 'kT', 'kT_halo', 'normalize', 'normalize_halo', 'halo'], d.distributionType == 'Thermal',
            ['distributionFile'], d.distributionType == 'File',
            ['species', 'charge'], d.distributionType != 'File' || isSDDS(),
            ['energy', 'particleCount'], d.distributionType != 'File',
        ]);
        panelState.showRow('distribution', 'lambdax', ! ['Thermal', 'File'].includes(d.distributionType));

    }
    $scope.whenSelected = updateFields;
    $scope.watchFields = [
        ['distribution.distributionType', 'distribution.distributionFile'], updateFields,
    ];
});
