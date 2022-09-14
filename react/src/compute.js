export function pollStateful({ doFetch, pollInterval, callback }) {
    let doIteration = () => {
        doFetch().then(async (resp) => {
            let respObj = await resp.json();
            let { state } = respObj;
            console.log("polled stateful compute: " + state);

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

    pollStateful({
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
