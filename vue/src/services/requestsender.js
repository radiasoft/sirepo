import { appState } from '@/services/appstate.js';
import { authState } from '@/services/authstate.js';
import { browserStorage } from '@/services/browserstorage.js';
import { msgRouter } from '@/services/msgrouter.js';
import { router } from '@/services/router.js';
import { uri } from '@/services/uri.js';

//TODO(pjm): logging service
const srlog = console.log;

const HTML_TITLE_RE = new RegExp('>([^<]+)</', 'i');
const IS_HTML_ERROR_RE = new RegExp('^(?:<html|<!doctype)', 'i');
const LOGIN_ROUTE_NAME = 'login';
//const LOGIN_URI = uri.formatLocal(LOGIN_ROUTE_NAME).slice(1);
const LOGIN_URI = '/login';
const REDIRECT_RE = new RegExp('window.location = "([^"]+)";', 'i');
const SR_EXCEPTION_RE = new RegExp('/\\*sr_exception=(.+)\\*/');
const storageKey = "previousRoute";
const TEXT_OR_JSON = new RegExp('^application/json$|^text');

//SIREPO.app.factory('requestSender', function(browserStorage, errorService,  msgRouter, uri, $location, $rootScope) {
class RequestSender {
    #srExceptionHandlers = [];
    //#listFilesData = {};

    #blobResponse(resp, successCallback, errorCallback) {
        // These two content-types are what the server might return with a 200.
        const d = resp.data;
        if (d instanceof Blob) {
            successCallback(d);
            return;
        }
        if (TEXT_OR_JSON.test(d.type)) {
            d.text().then((text) => {d = text;});
        }
        this.#errorResponse(
            {...resp, data: d},
            errorCallback,
        );
    }

    // #checkLoginRedirect(event, route) {
    //     if (! authState.isLoggedIn
    //         || authState.needCompleteRegistration
    //         || route.$$route && route.$$route.sirepoNoLoginRedirect
    //     ) {
    //         return;
    //     }

    //     let p = browserStorage.getString(storageKey);
    //     if (! p) {
    //         return;
    //     }
    //     browserStorage.removeItem(storageKey);
    //     p = p.split(' ');
    //     if (p[0] !== appState.schema.simulationType) {
    //         // wrong app so ignore
    //         return;
    //     }
    //     const r = uri.firstComponent(decodeURIComponent(p[1]));
    //     // After a reload from a login. Only redirect if
    //     // the route is different. The firstComponent is
    //     // always unique in our routes.
    //     if (uri.firstComponent($location.url()) !== r) {
    //         event.preventDefault();
    //         uri.localRedirect(decodeURIComponent(p[1]));
    //     }
    // }

    #defaultErrorCallback(data, status) {
        const err = appState.schema.customErrors[status];
        if (err && err.route) {
            uri.localRedirect(err.route);
        }
        else {
            //errorService.alertText('Request failed: ' + data.error);
            throw new Error('errorService not yet implemented');
        }
    }

    #errorResponse(resp, errorCallback) {
        let data = resp.data;
        let status = resp.status;
        let msg = null;
        if (status === 0) {
            msg = 'the server is unavailable';
            status = 503;
        }
        else if (status === -1) {
            msg = 'Server unavailable';
        }
        else if (appState.schema.customErrors[status]) {
            uri.localRedirect(appState.schema.customErrors[status].route);
            return;
        }
        if (typeof data === 'string' && IS_HTML_ERROR_RE.exec(data)) {
            // Try to parse javascript-redirect.html
            let m = SR_EXCEPTION_RE.exec(data);
            if (m) {
                // if this is invalid, will throw SyntaxError, which we
                // cannot handle so it will just show up as error.
                this.#handleSRException(JSON.parse(m[1]), errorCallback);
                return;
            }
            m = REDIRECT_RE.exec(data);
            if (m) {
                if (m[1].indexOf('#/error') <= -1) {
                    srlog('javascriptRedirectDocument', m[1]);
                    //uri.globalRedirect(m[1], undefined);
                    throw new Error('uri not yet implemented');
                    return;
                }
                srlog('javascriptRedirectDocument: staying on page', m[1]);
                // set explicitly so we don't log below
                data = {error: 'server error'};
            }
            else {
                // HTML document with error msg in title
                m = HTML_TITLE_RE.exec(data);
                if (m) {
                    srlog('htmlErrorDocument', m[1]);
                    data = {error: m[1]};
                }
            }
        }
        //if ($.isEmptyObject(data)) {
        //    data = {};
        //}
        //else
        if (! this.#isObject(data)) {
            errorService.logToServer(
                'serverResponseError', data, 'unexpected response type or empty');
            data = {};
        }
        if (! data.state) {
            data.state = 'error';
        }
        if (data.state == 'srException') {
            this.#handleSRException(data.srException, errorCallback);
            return;
        }
        if (! data.error) {
            if (msg) {
                data.error = msg;
            }
            else {
                srlog(resp);
                data.error = 'a server error occurred' + (status ? (': status=' + status) : '');
            }
        }
        srlog(data.error);
        errorCallback(data, status, resp.data);
    }

    #handleSRException = (srException, errorCallback) => {
        const e = srException;
        //TODO(robnagler) register handler
        // if (e.routeName == "httpRedirect") {
        //     uri.globalRedirect(e.params.uri, undefined);
        //     return;
        // }
        //TODO(robnagler) register handler
        // if (e.routeName == "serverUpgraded" && e.params && e.params.reason in SIREPO.refreshModalMap) {
        //     $(`#${SIREPO.refreshModalMap[e.params.reason].modal}`).modal('show');
        //     return;
        // }
	for (const h of this.#srExceptionHandlers) {
	    if (h(e, errorCallback)) {
                return;
            }
	}

        //TODO(robnagler) register handler
        // if (e.routeName == LOGIN_ROUTE_NAME) {
        //     saveLoginRedirect();
        //     // if redirecting to login, but the app thinks it is already logged in,
        //     // then force a logout to avoid a login loop
        //     if (authState.isLoggedIn) {
        //         uri.globalRedirect('authLogout');
        //         return;
        //     }
        // }

        uri.localRedirect(e.routeName, e.params);
    }

    #isObject(value) {
        return value !== null && typeof value === 'object';
    }

    // function saveLoginRedirect() {
    //     const u = $location.url();
    //     if (u == LOGIN_URI) {
    //         return;
    //     }
    //     browserStorage.setString(
    //         storageKey,
    //         appState.schema.simulationType + ' ' + encodeURIComponent(u),
    //     );
    // }

    registerSRExceptionHandler(handler) {
        if (this.#srExceptionHandlers.indexOf(handler) < 0) {
            this.#srExceptionHandlers.push(handler);
        }
    }

    unregisterSRExceptionHandler(handler) {
        const i = this.#srExceptionHandlers.indexOf(handler) < 0;
        if (i < 0) {
            throw new Error('Unknown SRExceptionHandler:', handler);
        }
        this.#srExceptionHandlers.splice(i, 1);
    }

    sendWithSimulationFields(url, successCallback, data, errorCb) {
        data.simulationId = data.simulationId || appState.models.simulation.simulationId;
        data.simulationType = appState.schema.simulationType;
        this.sendRequest(url, successCallback, data, errorCb);
    }

    // self.clearListFilesData = function() {
    //     listFilesData = {};
    // };

    // self.downloadRunFileUrl = (appState, params) => {
    //     return self.formatUrl(
    //         'downloadRunFile',
    //         {
    //             simulation_id: appState.models.simulation.simulationId,
    //             simulation_type: appState.schema.simulationType,
    //             frame: SIREPO.nonDataFileFrame,
    //             ...params
    //         },
    //     );
    // };

    // self.getListFilesData = function(name) {
    //     return listFilesData[name];
    // };

    // self.loadListFiles = function(name, params, callback) {
    //     if (listFilesData[name] || listFilesData[name + ".loading"]) {
    //         if (callback) {
    //             callback(listFilesData[name]);
    //         }
    //         return;
    //     }
    //     listFilesData[name + ".loading"] = true;
    //     msgRouter.send(
    //         uri.format('listFiles'),
    //         params,
    //         {}
    //     ).then(
    //         function(response) {
    //             const data = response.data;
    //             listFilesData[name] = data;
    //             delete listFilesData[name + ".loading"];
    //             if (callback) {
    //                 callback(data);
    //             }
    //         },
    //         function() {
    //             srlog(params, ' loadListFiles failed!');
    //             delete listFilesData[name + ".loading"];
    //             if (! listFilesData[name]) {
    //                 // if loading fails, use an empty list to prevent load requests on each digest cycle, see #1339
    //                 listFilesData[name] = [];
    //             }
    //         },
    //     );
    // };

    sendAnalysisJob(callback, data) {
        sendWithSimulationFields('analysisJob', callback, data);
    }

    sendRequest(routeName, successCallback, requestData, errorCallback) {
        if (typeof(routeName) != 'string') {
            throw new Error(`Invalid routeName, expecting string: ${routeName}`);
        }
        const httpConfig = {};
        if (! errorCallback) {
            errorCallback = this.#defaultErrorCallback;
        }
        if (! successCallback) {
            successCallback = () => {};
        }
        if (appState.schema.route[routeName].includes('<simulation_type>')) {
            //for (const f of ['simulation_type', 'simulationType']) {
            //requestData[f] = appState.simulationType;
            //}
            requestData.simulation_type = appState.simulationType;
        }
        else {
            requestData.simulationType = appState.simulationType;
        }
        if (requestData.responseType) {
            httpConfig.responseType = requestData.responseType;
            delete requestData.responseType;
        }
        msgRouter.send(
            appState.schema.route[routeName],
            requestData,
            httpConfig,
        ).then(
            (resp) => {
                if (httpConfig.responseType === 'blob') {
                    this.#blobResponse(resp, successCallback, errorCallback);
                    return;
                }
                // POSIT: typeof [] returns true
                if (! this.#isObject(resp.data) || resp.data.state === 'srException') {
                    this.#errorResponse(resp, errorCallback);
                    return;
                }
                successCallback(resp.data, resp.status);
            },
            (resp) => {
                this.#errorResponse(resp, errorCallback);
            },
        );
    }

    sendStatefulCompute(callback, data, errorCb) {
        sendWithSimulationFields('statefulCompute', callback, data, errorCb);
    }

    sendStatelessCompute(appState, successCallback, data, options={}) {
        // const maybeSetPanelState = (state) => {
        //     if (! options.panelState) {
        //         return;
        //     }
        //     options.panelState.maybeSetState(options.modelName, state);
        // };

        const onError = (data) => {
            srlog('statelessCompute error: ', data.error);
            if (options.onError) {
                options.onError(data);
                return;
            }
            // maybeSetPanelState('error');
        };

        // maybeSetPanelState('loading');
        sendWithSimulationFields(
            'statelessCompute',
            (data) => {
                if (data.state === 'error') {
                    onError(data);
                    return;
                }
                // maybeSetPanelState('loadingDone');
                successCallback(data);
            },
            data,
            onError
        );
    }

    //$rootScope.$on('$routeChangeStart', #checkLoginRedirect);
    //return self;
}

export const requestSender = new RequestSender();

requestSender.registerSRExceptionHandler((srException, errorCallback) => {
    if (srException.routeName === 'httpRedirect') {
        uri.globalRedirect(srException.params.uri);
        return true;
    }
});
