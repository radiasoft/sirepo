import {
    Col,
    Row,
    Container,
    Nav,
    Navbar
} from "react-bootstrap";
import {
    useState,
    useEffect,
    useContext
} from "react";
import {
    ContextAppName,
    ContextSimulationListPromise,
    ContextRelativeRouterHelper,
    ContextLayouts,
    ContextSchema,
    ContextModelsWrapper,
    ContextSimulationInfoPromise,
    ContextReportEventManager
} from "../context";
import {
    updateModel,
    selectModel,
    selectModels
} from "../store/models";
import { ModelsWrapper } from "../data/model";
import { FormStateInitializer } from "../component/form";
import { useResolvedPath } from "react-router-dom";
import { RouteHelper } from "../hook/route";
import { ReportEventManager } from "../data/report";
import { SrNavbar } from "./navbar";

function SimulationInfoInitializer(props) {
    let { simulation } = props;

    let [simulationInfoPromise, updateSimulationInfoPromise] = useState(undefined);
    let [hasInit, updateHasInit] = useState(false);
    let appName = useContext(ContextAppName);

    let modelsWrapper = new ModelsWrapper({
        modelActions: {
            updateModel
        },
        modelSelectors: {
            selectModel,
            selectModels
        }
    })

    useEffect(() => {
        updateSimulationInfoPromise(new Promise((resolve, reject) => {
            let { simulationId } = simulation;
            // TODO: why 0
            fetch(`/simulation/${appName}/${simulationId}/0/source`).then(async (resp) => {
                let simulationInfo = await resp.json();
                let { models } = simulationInfo;

                for(let [modelName, model] of Object.entries(models)) {
                    modelsWrapper.updateModel(modelName, model);
                }

                resolve({...simulationInfo, simulationId});
                updateHasInit(true);
            })
        }))
    }, [])

    return hasInit && simulationInfoPromise && (
        <ContextModelsWrapper.Provider value={modelsWrapper}>
            <ContextSimulationInfoPromise.Provider value={simulationInfoPromise}>
                {props.children}
            </ContextSimulationInfoPromise.Provider>
        </ContextModelsWrapper.Provider>
    )
}

function ReportEventManagerInitializer(props) {
    return <ContextReportEventManager.Provider value={new ReportEventManager()}>
        {props.children}
    </ContextReportEventManager.Provider>
}

export function SimulationOuter(props) {
    let appName = useContext(ContextAppName);

    let simBrowerRelativeRouter = useContext(ContextRelativeRouterHelper);

    let pathPrefix = useResolvedPath('');
    let currentRelativeRouter = new RouteHelper(pathPrefix);


    // TODO: navbar should route to home, when one is made
    return (
        <Container fluid>
            <SrNavbar title={appName.toUpperCase()} titleHref={simBrowerRelativeRouter.getCurrentPath()}>
            </SrNavbar>
            <ContextRelativeRouterHelper.Provider value={currentRelativeRouter}>
                {props.children}
            </ContextRelativeRouterHelper.Provider>
        </Container>

    )

}

export function SimulationRoot(props) {
    let { simulation } = props;

    let layouts = useContext(ContextLayouts);

    let schema = useContext(ContextSchema);

    let viewComponents = schema.views.map((view, index) => {
        let layout = layouts.getLayoutForConfig(view);
        let Component = layout.component;
        return (
            <Component config={view} key={index}></Component>
        )
    });

    // TODO: use multiple rows
    return (
        <SimulationOuter>
            <ReportEventManagerInitializer>
                <SimulationInfoInitializer simulation={simulation}>
                    <FormStateInitializer>
                        {viewComponents}
                    </FormStateInitializer>
                </SimulationInfoInitializer>
            </ReportEventManagerInitializer>
        </SimulationOuter>
    )
}
