import { useContext, useState, useRef, useEffect } from "react";
import { Dependency } from "../data/dependency";
import { ContextSimulationInfoPromise, ContextAppName, ContextRelativeFormDependencies, ContextModelsWrapper, ContextLayouts } from "../context";
import { useDependentValues } from "../hook/dependency";
import { View } from "./layout";
import { pollRunReport } from "../utility/compute";

export class AutoRunReportLayout extends View {
    getFormDependencies = (config) => {
        // TODO
        return [];
    }

    component = (props) => {
        let { config } = props;
        let { report, reportLayout, dependencies } = config;

        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);
        let appName = useContext(ContextAppName);
        let modelsWrapper = useContext(ContextModelsWrapper);
        let layouts = useContext(ContextLayouts);

        let formDependencies = useContext(ContextRelativeFormDependencies);
        let reportDependencies = dependencies.map(dependencyString => new Dependency(dependencyString));

        let dependentValues = useDependentValues(modelsWrapper, [...formDependencies, ...reportDependencies]);

        let [simulationData, updateSimulationData] = useState(undefined);

        let simulationPollingVersionRef = useRef()

        useEffect(() => {
            updateSimulationData(undefined);
            let pollingVersion = {};
            simulationPollingVersionRef.current = pollingVersion;
            simulationInfoPromise.then(({ models, simulationId, simulationType, version }) => {
                console.log("starting to poll report");
                pollRunReport({
                    appName,
                    models,
                    simulationId,
                    report: report,
                    pollInterval: 500,
                    callback: (simulationData) => {
                        console.log("polling report yielded new data");
                        // guard concurrency
                        if(simulationPollingVersionRef.current == pollingVersion) {
                            updateSimulationData(simulationData);
                        } else {
                            console.log("polling data was not from newest request");
                        }
                    }
                })
            })
        }, dependentValues)    

        let layoutElement = layouts.getLayoutForConfig(reportLayout);

        let VisualComponent = simulationData ? layoutElement.component : undefined;

        return (
            <>
                {VisualComponent && <VisualComponent config={config} simulationData={simulationData}></VisualComponent>}
            </>
        )
    }
}
