'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('JupyterhubMigrateController', function(authState, jupyterhubloginService, requestSender, $scope) {
    const self = this;
    self.isLoading = true;
    requestSender.sendRequest(
        'redirectJupyterHub',
        () => {self.isLoading = false;}
    );
    self.migrate = function(doMigration) {
        jupyterhubloginService.doMigration(doMigration);
    };
});

SIREPO.app.controller('NameConflictController', function(requestSender, jupyterhubloginService, $route, $scope) {
    const self = this;
    self.isMigration = $route.current.params.isMigration;

    self.noMigration = function() {
        jupyterhubloginService.doMigration(false);
    };

    self.logout = function() {
        requestSender.globalRedirect(
            'authLogout',
            {'<simulation_type>': SIREPO.APP_SCHEMA.simulationType,}
        );
    };
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

SIREPO.app.factory('jupyterhubloginService', function(appState, requestSender) {
    const self = {};
    appState.setAppService(self);

    self.doMigration = function(doMigration) {
        requestSender.sendRequest(
            'migrateJupyterhub',
            null,
            {doMigration: doMigration}
        );
    };
    return self;
});
