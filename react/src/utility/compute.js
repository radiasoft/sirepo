export function pollCompute({ doFetch, pollInterval, callback }) {
    let iterate = () => {
        doFetch().then(async (resp) => {
            let respObj = await resp.json();
            let { state } = respObj;

            if (state === 'pending' || state === 'running') {
                setTimeout(iterate, pollInterval);
            }

            callback(respObj);
        })
    }

    iterate();
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

export function pollRunReport({ appName, models, simulationId, report, pollInterval, callback, forceRun }) {
    let doFetch = () => fetch('/run-simulation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            models,
            forceRun,
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

    let iterate = async (lastResp) => {
        let respObj = await lastResp.json();
        let { nextRequest, state } = respObj;

        callback(respObj);
        
        if (!state || state === 'pending' || state === 'running') {
            setTimeout(() => doPoll(nextRequest).then(iterate), pollInterval);
        }
    } 

    doFetch().then(iterate);
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

export function getSimulationFrame(frameId) {
    return new Promise((resolve, reject) => {
        fetch(`/simulation-frame/${frameId}`).then(async (resp) => {
            let respObj = await resp.json();
            resolve(respObj);
        })
    })
}
