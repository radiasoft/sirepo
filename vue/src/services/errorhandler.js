
import { schema } from '@/services/schema.js';
import { singleton } from '@/services/singleton.js';
import { uri } from '@/services/uri.js';

//TODO(pjm): logging service
const srlog = console.log;

class ErrorHandler {
    #errorHandlers = [];

    handleError(err) {
	for (const h of this.#errorHandlers) {
	    if (h(err)) {
                return;
            }
	}

        //TODO(pjm): will need to incorporate all error handling from legacy RequestSender

        if (err && err.data && err.data.state === 'srException') {
            const e = err.data.srException;
            if (e.routeName === 'httpRedirect') {
                uri.globalRedirect(e.params.uri);
                return true;
            }
            uri.localRedirect(e.routeName, e.params);
            return;
        }
        if (err && err.status && schema.customErrors[err.status]) {
            uri.localRedirect(schema.customErrors[err.status].route);
            return;
        }
        srlog(err.message, err.stack);
        this.logToServer('clientException', err.message, '', err.stack);
        //TODO(pjm): show error alert on client
    }

    logToServer = function(errorType, message, cause, stackTrace) {
        fetch(schema.route.errorLogging, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: window.location.href,
                message: message,
                type: errorType,
                stackTrace: stackTrace,
                cause: cause,
            }),
        }).catch((err) => {
            srlog('logToServer failed:', err);
        });
    }

    registerErrorHandler(handler) {
        if (this.#errorHandlers.indexOf(handler) < 0) {
            this.#errorHandlers.push(handler);
        }
    }

    unregisterErrorHandler(handler) {
        const i = this.#errorHandlers.indexOf(handler) < 0;
        if (i < 0) {
            throw new Error('Unknown errorHandler:', handler);
        }
        this.#errorHandlers.splice(i, 1);
    }
}

export const errorHandler = singleton.add('errorHandler', () => new ErrorHandler());

export const onError = (err) => {
    errorHandler.handleError(err);
};
