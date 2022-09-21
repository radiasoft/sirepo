export function pollCompute({ doFetch, pollInterval, callback }) {
    console.log("started polling compute");
    let doIteration = () => {
        doFetch().then(async (resp) => {
            let respObj = await resp.json();
            let { state } = respObj;
            console.log("polled compute: " + state);

            if (state === 'pending' || state === 'running') {
                setTimeout(doIteration, pollInterval);
            }

            callback(respObj);
        })
    }

    doIteration();
}

export function pollStatefulCompute({ pollInterval, method, simulationId, appName, callback }) {
    let doFetch = () => fetch('/stateful-compute', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            method,
            simulationId,
            simulationType: appName
        })
    });

    pollCompute({
        doFetch,
        pollInterval,
        callback: (respObj) => {
            let { state } = respObj;

            if(state === 'completed') {
                callback(respObj);
            }
        }
    })
}

export function pollRunReport({ appName, models, simulationId, report, pollInterval, callback }) {
    let doFetch = () => fetch('/run-simulation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            models,
            forceRun: false,
            report,
            simulationId,
            simulationType: appName
        })
    });

    let doPoll = (nextRequest) => fetch('/run-status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            ...nextRequest
        })
    });

    let doIteration = async (lastResp) => {
        let respObj = await lastResp.json();
        let { nextRequest, state } = respObj;

        callback(respObj);
        
        if (!state || state === 'pending' || state === 'running') {
            setTimeout(() => doPoll(nextRequest).then(doIteration), pollInterval);
        }
    } 

    doFetch().then(doIteration);
}

export function cancelReport({ appName, models, simulationId, report }) {
    return fetch('/run-cancel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            models,
            forceRun: false,
            report,
            simulationId,
            simulationType: appName
        })
    })
}
