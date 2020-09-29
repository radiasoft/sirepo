'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('JupyterhubloginController', function(authState, requestSender, $sce,  $scope) {
    if (
            ! authState.isLoggedIn ||
            authState.rsMigrationDone ||
            authState.rsMigrationPromptDimsissed
    ) {
        requestSender.sendRequest('redirectJupyterHub');
        return;
    }
    const self = this;
    self.dismissChecked = false;

    self.dismissRsMigrationPrompt = function(v) {
        requestSender.sendRequest('dismissJupyterhubDataMovePrompt', null, {dismiss: self.dismissChecked});
    }

    self.migrate = function(doMigration) {
        if (! doMigration) {
            requestSender.sendRequest('redirectJupyterHub');
            return;
        }
        requestSender.globalRedirect(
            'migrateRsJupyterhubData',
            {'<simulation_type>': SIREPO.APP_SCHEMA.simulationType}
        );
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
