'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('JupyterhubloginController', function(authState, requestSender, $sce,  $scope) {
    const self = this;
    self.isLoading = true;
    requestSender.sendRequest(
        'redirectJupyterHub',
        () => {self.isLoading = false;}
    );
    self.migrate = function(doMigration) {
        requestSender.sendRequest(
            'migrateRsJupyterhubData',
            null,
            {doMigration: doMigration}
        )
    }
});

SIREPO.app.directive('appHeader', function(jupyterhubloginService) {
    return {
	restrict: 'A',
	scope: {
            nav: '=appHeader',
	},
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-right="nav"></div>',
	].join('')
    };
});

SIREPO.app.factory('jupyterhubloginService', function(appState) {
    const self = {};
    appState.setAppService(self);
    return self;
});
