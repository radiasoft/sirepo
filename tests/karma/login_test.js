'use strict';
beforeEach(module('SirepoApp'));

describe('OpenID Connect login', function() {
    it('should retain the method chooser in mixed deployments', inject(function($controller) {
        const requestSender = {
            localRedirect: jasmine.createSpy('localRedirect'),
        };
        $controller('LoginController', {
            authService: {},
            authState: {isLoggedIn: false, visibleMethods: ['email', 'oidc']},
            requestSender: requestSender,
        });
        expect(requestSender.localRedirect).not.toHaveBeenCalled();
    }));

    it('should select a sole OIDC method through the normal login page', inject(function($controller) {
        const requestSender = {
            localRedirect: jasmine.createSpy('localRedirect'),
        };
        $controller('LoginController', {
            authService: {},
            authState: {isLoggedIn: false, visibleMethods: ['oidc']},
            requestSender: requestSender,
        });
        expect(requestSender.localRedirect).toHaveBeenCalledWith(
            'loginWith', {':method': 'oidc'}
        );
    }));

    it('should start OIDC with browser navigation rather than an API request', inject(function($controller) {
        const requestSender = {
            globalRedirect: jasmine.createSpy('globalRedirect'),
            sendRequest: jasmine.createSpy('sendRequest'),
        };
        $controller('LoginWithController', {
            authState: {},
            errorService: {},
            requestSender: requestSender,
            uri: {currentRouteParam: () => 'oidc'},
        });
        expect(requestSender.globalRedirect).toHaveBeenCalledWith(
            'authOidcLogin', {simulation_type: SIREPO.APP_SCHEMA.simulationType}
        );
        expect(requestSender.sendRequest).not.toHaveBeenCalled();
    }));

    [
        {method: 'oidc', moderated: false},
        {method: 'oidc', moderated: true},
        {method: 'email', moderated: false},
    ].forEach(function(test) {
        it('should complete ' + test.method + ' registration with moderation=' + test.moderated, inject(function($controller) {
            const previous = SIREPO.authState;
            const authState = {
                method: test.method,
                isModerated: test.moderated,
                handleLogin: jasmine.createSpy('handleLogin'),
            };
            const requestSender = {
                sendRequest: jasmine.createSpy('sendRequest'),
            };
            spyOn($.fn, 'modal');
            try {
                SIREPO.authState = {
                    isLoggedIn: test.method !== 'oidc',
                    needCompleteRegistration: test.method !== 'oidc',
                };
                const controller = $controller('LoginConfirmController', {
                    authState: authState,
                    requestSender: requestSender,
                    $route: {
                        current: {
                            params: {},
                            oidcRegistration: test.method === 'oidc',
                            templateUrl: 'complete-registration.html',
                        },
                    },
                });
                controller.data = {displayName: 'OIDC User', reason: 'Research'};
                controller.submit();
                const args = requestSender.sendRequest.calls.mostRecent().args;
                expect(args[0]).toBe(
                    test.method === 'oidc' ? 'authOidcCompleteRegistration' : 'authCompleteRegistration'
                );
                expect(args[2]).toEqual({
                    displayName: 'OIDC User',
                    reason: 'Research',
                    simulationType: SIREPO.APP_NAME,
                });
                args[1]({state: 'ok'});
                if (test.moderated) {
                    expect($.fn.modal).toHaveBeenCalledWith('show');
                    expect(authState.handleLogin).not.toHaveBeenCalled();
                }
                else {
                    expect(authState.handleLogin).toHaveBeenCalledWith({state: 'ok'}, controller);
                    expect($.fn.modal).not.toHaveBeenCalled();
                }
            }
            finally {
                SIREPO.authState = previous;
            }
        }));
    });
});
