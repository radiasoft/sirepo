'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.controller('JupyterloginController', function(requestSender) {
    requestSender.sendRequest('redirectJupyterHub');
});

SIREPO.app.directive('appHeader', function(jupyterhubloginService) {
    return {
	restrict: 'A',
	scope: {
            nav: '=appHeader',
	},
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav"></div>',
	].join('')
    };
});

SIREPO.app.factory('jupyterhubloginService', function(appState) {
    const self = {};
    appState.setAppService(self);
    return self;
});
