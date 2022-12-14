import {
    Container
} from "react-bootstrap";
import React, {
    useState,
    useEffect,
    useContext
} from "react";
import {
    modelSelectors,
    modelActions,
    ModelState
} from "../store/models";
import { FormStateInitializer } from "./reusable/form";
import { useResolvedPath } from "react-router-dom";
import { CRelativeRouterHelper, RouteHelper } from "../utility/route";
import { ReportEventManager } from "../data/report";
import { CReportEventManager } from "../data/report";
import { CModelsWrapper, ModelsWrapper } from "../data/wrapper";
import { CAppName, CSchema, CSimulationInfoPromise } from "../data/appwrapper";
import { LAYOUTS } from "../layout/layouts";
import { ModelsAccessor } from "../data/accessor";
import { Dependency } from "../data/dependency";

function SimulationInfoInitializer(props) {
    let { simulation } = props;

    let [simulationInfoPromise, updateSimulationInfoPromise] = useState(undefined);
    let [hasInit, updateHasInit] = useState(false);
    let appName = useContext(CAppName);

    let modelsWrapper = new ModelsWrapper({
        modelActions,
        modelSelectors
    })

    useEffect(() => {
        updateSimulationInfoPromise(new Promise((resolve, reject) => {
            let { simulationId } = simulation;
            // TODO: why 0
            fetch(`/simulation/${appName}/${simulationId}/0/source`).then(async (resp) => {
                let simulationInfo = await resp.json();
                let models = simulationInfo['models'] as ModelState[];

                for(let [modelName, model] of Object.entries(models)) {
                    modelsWrapper.updateModel(modelName, model);
                }

                resolve({...simulationInfo, simulationId});
                updateHasInit(true);
            })
        }))
    }, [])

    return hasInit && simulationInfoPromise && (
        <CModelsWrapper.Provider value={modelsWrapper}>
            <CSimulationInfoPromise.Provider value={simulationInfoPromise}>
                {props.children}
            </CSimulationInfoPromise.Provider>
        </CModelsWrapper.Provider>
    )
}

function ReportEventManagerInitializer(props) {
    return <CReportEventManager.Provider value={new ReportEventManager()}>
        {props.children}
    </CReportEventManager.Provider>
}

export function SimulationOuter(props) {

    let pathPrefix = useResolvedPath('');
    let currentRelativeRouter = new RouteHelper(pathPrefix);

    let modelsWrapper = useContext(CModelsWrapper);
    let simNameDep = new Dependency("simulation.name");
    let simNameAccessor = new ModelsAccessor(modelsWrapper, [simNameDep]);

    useEffect(() => {
        document.title = simNameAccessor.getFieldValue(simNameDep) as string;
    })

    // TODO: navbar should route to home, when one is made
    return (
        <Container fluid>
            <CRelativeRouterHelper.Provider value={currentRelativeRouter}>
                {props.children}
            </CRelativeRouterHelper.Provider>
        </Container>

    )

}

export function SimulationRoot(props) {
    let { simulation } = props;

    let schema = useContext(CSchema);

    let layoutComponents = schema.views.map((schemaLayout, index) => {
        // this should not be called here. it is dangerous to generate layouts on render
        // this is an exception for now as no updates should occur above this element
        // besides changing apps
        let layout = LAYOUTS.getLayoutForSchema(schemaLayout);
        let Component = layout.component;
        return (
            <Component key={index}></Component>
        )
    });

    // TODO: use multiple rows
    return (    
        <SimulationInfoInitializer simulation={simulation}>
            <SimulationOuter>
                <ReportEventManagerInitializer>
                    <FormStateInitializer>
                        {layoutComponents}
                    </FormStateInitializer>
                </ReportEventManagerInitializer>
            </SimulationOuter>
        </SimulationInfoInitializer>    
    )
}
