
//TODO(pjm): logging service
const srlog = console.log;

import { requestSender } from '@/services/requestsender.js';
import { schema } from '@/services/schema.js';
import { singleton } from '@/services/singleton.js';
import { util } from '@/services/util.js';

// qState
const _PENDING = 'pending';
const _PROCESSING = 'processing';
const _DONE = 'done';
const _REMOVING = 'removing';
const _CANCELED = 'canceled';

// qMode
const _PERSISTENT_STATUS = 'persistentStatus';
const _PERSISTENT = 'persistent';
const _TRANSIENT = 'transient';

class SimQueue {
    #runQueue = [];

    #addItem(report, models, responseHandler, qMode) {
        models = util.clone(models);
        // simulationStatus is not used server side
        delete models.simulationStatus;
        const qi = {
            firstRoute: qMode === _PERSISTENT_STATUS ? 'runStatus' : 'runSimulation',
            qMode: qMode,
            persistent: qMode.indexOf('persistent') > -1,
            // qState: pending, processing, done, removing, canceled
            qState: _PENDING,
            runStatusCount: 0,
            request: {
                forceRun: qMode === _PERSISTENT,
                report: report,
                models: models,
                simulationType: schema.simulationType,
                simulationId: models.simulation.simulationId,
            },
            responseHandler: responseHandler,
        };
        this.#runQueue.push(qi);
        if (qi.persistent) {
            this.#runItem(qi);
        }
        else {
            this.#runFirstTransientItem();
        }
        return qi;
    }

    #cancelTimeout(qi) {
        if (qi.timeout) {
            clearTimeout(qi.timeout);
            qi.timeout = null;
        }
    }

    #handleResult(qi, resp) {
        qi.qState = _DONE;
        this.removeItem(qi);
        qi.responseHandler(resp);
        this.#runFirstTransientItem();
    }

    #runFirstTransientItem() {
        for (const e of this.#runQueue) {
            if (e.persistent) {
                continue;
            }
            if (e.qState === _PENDING) {
                this.#runItem(e);
            }
            break;
        }
    }

    async #runItem(qi) {
        const handleStatus = (qi, resp) => {
            qi.request = resp.nextRequest;
            //TODO(pjm): ignore if a runStatis is already pending for this queueItem?
            if (! qi.timeout) {
                qi.timeout = setTimeout(
                    async () => {
                        qi.timeout = null;
                        qi.runStatusCount++;
                        process(await requestSender.sendRequest('runStatus', qi.request));
                    },
                    // Sanity check in case of defect on server
                    Math.max(1, resp.nextRequestSeconds) * 1000,
                );
            }
            if (qi.persistent) {
                qi.responseHandler(resp);
            }
        };

        const process = (resp) => {
            if (qi.qState === _REMOVING) {
                return;
            }
            if (resp.state === 'running' || resp.state === _PENDING) {
                handleStatus(qi, resp);
            }
            else {
                this.#handleResult(qi, resp);
            }
        };

        this.#cancelTimeout(qi);
        qi.qState = _PROCESSING;
        //TODO(pjm): this call does not return immediately if the server is "Waiting for another sim op to complete"
        const r = await requestSender.sendRequest(qi.firstRoute, qi.request)
        if (qi.qState !== _REMOVING) {
            process(r);
        }
    }

    addPersistentStatusItem(report, models, responseHandler) {
        return this.#addItem(report, models, responseHandler, _PERSISTENT_STATUS);
    }

    addPersistentItem(report, models, responseHandler) {
        return this.#addItem(report, models, responseHandler, _PERSISTENT);
    }

    addTransientItem(report, models, responseHandler) {
        return this.#addItem(report, models, responseHandler, _TRANSIENT);
    }

    cancelItem(qi) {
        qi.qMode = _TRANSIENT;
        const isProcessingTransient = qi.qState === _PROCESSING && ! qi.persistent;
        if (qi.qState === _PROCESSING) {
            requestSender.sendRequest('runCancel', qi.request);
            qi.qState = _CANCELED;
        }
        this.removeItem(qi);
        if (isProcessingTransient) {
            this.#runFirstTransientItem();
        }
    }

    cancelTransientItems() {
        const rq = this.#runQueue;
        this.#runQueue = [];
        rq.forEach((item) => {
            if (item.qMode === _TRANSIENT) {
                this.removeItem(item);
            }
            else {
                this.#runQueue.push(item);
            }
        });
    }

    removeItem(qi) {
        const qs = qi.qState;
        if (qs === _REMOVING) {
            return;
        }
        qi.qState = _REMOVING;
        // look for report match, qi might be a Proxy object
        for (let i = 0; i < this.#runQueue.length; i++) {
            if (this.#runQueue[i].request.report === qi.request.report) {
                this.#runQueue.splice(i, 1);
                break;
            }
        }
        this.#cancelTimeout(qi);
        if (qs === _PROCESSING && ! qi.persistent) {
            requestSender.sendRequest('runCancel', qi.request);
        }
    }

    //$rootScope.$on('clearCache', this.cancelTransientItems);
}

export const simQueue = singleton.add('simQueue', () => new SimQueue());
