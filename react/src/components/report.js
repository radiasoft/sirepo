import { useContext, useState, useEffect } from "react";
import { Dependency, useDependentValues } from "../dependency";
import { ContextSimulationInfoPromise, ContextAppName, ContextRelativeHookedDependencyGroup, ContextRelativeFormDependencies, ContextModels } from "./context";
import { Panel } from "./panel";

function pollRunReport({ appName, models, simulationId, report, pollInterval}) {
    return new Promise((resolve, reject) => {
        let doFetch = () => {
            fetch('/run-simulation', {
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
            }).then(async (resp) => {
                let simulationStatus = await resp.json();
                console.log("status", simulationStatus);
                let { state } = simulationStatus;
                console.log("polled report: " + state);
                if(state === 'completed') {
                    resolve(simulationStatus);
                } else if (state === 'pending') {
                    setTimeout(doFetch, pollInterval); // TODO
                } else {
                    reject();
                }
            })
        }
        doFetch();
    })
}

export function AutoRunReportLayout(layoutElement) {
    return {
        getDependencies: layoutElement.getDependencies,

        element: (props) => {
            let { config } = props;
            let { report } = config;

            let dependencyStrings = config.dependencies;
    
            let contextFn = useContext;
            let stateFn = useState;
            let effectFn = useEffect;
            let dependentValuesFn = useDependentValues;
    
            let simulationInfoPromise = contextFn(ContextSimulationInfoPromise);
            let appName = contextFn(ContextAppName);
            let modelsWrapper = contextFn(ContextModels);

            let formDependencies = contextFn(ContextRelativeFormDependencies);
            let reportDependencies = dependencyStrings.map(dependencyString => new Dependency(dependencyString));

            let dependentValues = dependentValuesFn(modelsWrapper, [...formDependencies, ...reportDependencies]);

            console.log("dependentValues", dependentValues);
    
            let [simulationData, updateSimulationData] = stateFn(undefined);
    
            effectFn(() => {
                updateSimulationData(undefined);
                let simulationDataPromise = new Promise((resolve, reject) => {
                    simulationInfoPromise.then(({ models, simulationId, simulationType, version }) => {
                        console.log("starting to poll report");
                        pollRunReport({
                            appName,
                            models,
                            simulationId,
                            report: report,
                            pollInterval: 500
                        }).then((simulationData) => {
                            console.log("finished polling report");
                            resolve(simulationData);
                        })
                    })
                });
        
                simulationDataPromise.then(updateSimulationData);
            }, dependentValues)
    
            
    
            let VisualComponent = simulationData ? layoutElement.element : undefined;
            //let VisualComponent = layoutElement.element;
    
            return (
                <>
                    {VisualComponent && <VisualComponent config={config} simulationData={simulationData}></VisualComponent>}
                </>
            )
        }
    }
}
