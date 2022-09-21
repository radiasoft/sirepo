import { useContext, useState, useRef, useEffect } from "react";
import { Dependency } from "../data/dependency";
import { ContextSimulationInfoPromise, ContextAppName, ContextRelativeFormDependencies, ContextModelsWrapper, ContextLayouts } from "../context";
import { useDependentValues } from "../hook/dependency";
import { View } from "./layout";
import { pollRunReport } from "../utility/compute";
import { v4 as uuidv4 } from 'uuid';

export class AutoRunReportLayout extends View {
    getFormDependencies = (config) => {
        let { reportLayout } = config;
        let layoutElement = this.layoutsWrapper.getLayoutForConfig(reportLayout);
        return layoutElement.getFormDependencies();
    }

    component = (props) => {
        let { config } = props;
        let { report, reportLayout, dependencies } = config;

        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);
        let appName = useContext(ContextAppName);
        let modelsWrapper = useContext(ContextModelsWrapper);

        let formDependencies = useContext(ContextRelativeFormDependencies);
        let reportDependencies = dependencies.map(dependencyString => new Dependency(dependencyString));

        let dependentValues = useDependentValues(modelsWrapper, [...formDependencies, ...reportDependencies]);

        let [simulationData, updateSimulationData] = useState(undefined);

        let simulationPollingVersionRef = useRef(uuidv4())

        useEffect(() => {
            updateSimulationData(undefined);
            let pollingVersion = uuidv4();
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
                        console.log("polling report yielded new data", simulationData);
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

        let layoutElement = this.layoutsWrapper.getLayoutForConfig(reportLayout);

        let VisualComponent = simulationData ? layoutElement.component : undefined;

        // set the key as the key for the latest request sent to make a brand new report component for each new request data
        return (
            <>
                {VisualComponent && <VisualComponent key={simulationPollingVersionRef.current} config={reportLayout} simulationData={simulationData}></VisualComponent>}
            </>
        )
    }
}

export class ManualRunReportLayout extends View {
    getFormDependencies = (config) => {
        let { reportLayout } = config;
        let layoutElement = this.layoutsWrapper.getLayoutForConfig(reportLayout);
        return layoutElement.getFormDependencies();
    }


}
