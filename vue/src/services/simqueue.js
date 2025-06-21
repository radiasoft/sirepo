
//TODO(pjm): logging service
const srlog = console.log;

import { appState } from '@/services/appstate.js';
import { requestSender } from '@/services/requestsender.js';
import { util } from '@/services/util.js';

class SimQueue {
    runQueue = [];

    #addItem(report, models, responseHandler, qMode) {
        models = util.clone(models);
        // simulationStatus is not used server side
        delete models.simulationStatus;
        const qi = {
            firstRoute: qMode === 'persistentStatus' ? 'runStatus' : 'runSimulation',
            qMode: qMode,
            persistent: qMode.indexOf('persistent') > -1,
            // qState: pending, processing, done, removing, canceled
            qState: 'pending',
            runStatusCount: 0,
            request: {
                forceRun: qMode === 'persistent',
                report: report,
                models: models,
                simulationType: appState.simulationType,
                simulationId: models.simulation.simulationId,
            },
            responseHandler: responseHandler,
        };
        this.runQueue.push(qi);
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
        qi.qState = 'done';
        this.removeItem(qi);
        qi.responseHandler(resp);
        this.#runFirstTransientItem();
    }

    #runFirstTransientItem() {
        for (const e of this.runQueue) {
            if (e.persistent) {
                continue;
            }
            if (e.qState === 'pending') {
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
            if (qi.qState === 'removing') {
                return;
            }
            if (resp.state === 'running' || resp.state === 'pending') {
                handleStatus(qi, resp);
            }
            else {
                this.#handleResult(qi, resp);
            }
        };

        this.#cancelTimeout(qi);
        qi.qState = 'processing';
        process(await requestSender.sendRequest(qi.firstRoute, qi.request));
    }

    addPersistentStatusItem(report, models, responseHandler) {
        return this.#addItem(report, models, responseHandler, 'persistentStatus');
    }

    addPersistentItem(report, models, responseHandler) {
        return this.#addItem(report, models, responseHandler, 'persistent');
    }

    addTransientItem(report, models, responseHandler) {
        return this.#addItem(report, models, responseHandler, 'transient');
    }

    cancelItem(qi) {
        qi.qMode = 'transient';
        const isProcessingTransient = qi.qState === 'processing' && ! qi.persistent;
        if (qi.qState === 'processing') {
            requestSender.sendRequest('runCancel', qi.request);
            qi.qState = 'canceled';
        }
        this.removeItem(qi);
        if (isProcessingTransient) {
            this.#runFirstTransientItem();
        }
    }

    cancelTransientItems() {
        const rq = this.runQueue;
        this.runQueue = [];
        rq.forEach((item) => {
            if (item.qMode === 'transient') {
                this.removeItem(item);
            }
            else {
                this.runQueue.push(item);
            }
        });
    }

    removeItem(qi) {
        const qs = qi.qState;
        if (qs === 'removing') {
            return;
        }
        qi.qState = 'removing';
        const i = this.runQueue.indexOf(qi);
        if (i > -1) {
            this.runQueue.splice(i, 1);
        }
        this.#cancelTimeout(qi);
        if (qs === 'processing' && ! qi.persistent) {
            requestSender.sendRequest('runCancel', qi.request);
        }
    }

    //$rootScope.$on('clearCache', this.cancelTransientItems);
}

export const simQueue = new SimQueue();
