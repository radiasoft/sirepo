import {
    Button,
    Col,
    Container, Dropdown, Form, Modal, Row
} from "react-bootstrap";
import React, {
    useState,
    useEffect,
    useContext
} from "react";
import {
    modelSelectors,
    modelActions,
    ModelState,
    modelsSlice
} from "../store/models";
import { FormStateInitializer } from "./reusable/form";
import { useNavigate, useResolvedPath } from "react-router-dom";
import { CRelativeRouterHelper, CRouteHelper, RelativeRouteHelper } from "../utility/route";
import { ReportEventManager } from "../data/report";
import { CReportEventManager } from "../data/report";
import { CAppName, CSchema, CSimulationInfoPromise } from "../data/appwrapper";
import { LAYOUTS } from "../layout/layouts";
import { Dependency } from "../data/dependency";
import { NavbarRightContainerId, NavToggleDropdown } from "./reusable/navbar";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { useSetup } from "../hook/setup";
import { Portal } from "./reusable/portal";
import { downloadAs, getAttachmentFileName } from "../utility/download";
import { Provider, useDispatch, useStore } from "react-redux";
import { ArrayFieldState, StoreState } from "../store/common";
import { configureStore, Middleware } from "@reduxjs/toolkit";
import { formActions, formSelectors, formStatesSlice } from "../store/formState";
import { BaseHandleFactory, CHandleFactory } from "../data/handle";
import { getValueSelector, newModelFromSchema, StoreType, StoreTypes } from "../data/data";
import { useCoupledState } from "../hook/coupling";

export type SimulationInfoRaw = {
    models: StoreState<ModelState>,
    simulationType: string,
    version: string
}

export type SimulationInfo = SimulationInfoRaw & {
    simulationId: string
}

function SimulationStoreInitializer(props: {[key: string]: any}) {
    let schema = useContext(CSchema);

    let shadowBeamlineWatchpointReportsMiddleware: Middleware = store => next => action => {
        if(action.type === "models/updateModel") {
            let { name, value } = action.payload;
            if(name === "beamline") {
                let watchpointReportsModel: ModelState = modelSelectors.selectModel("watchpointReports")(store.getState());
                if(watchpointReportsModel) {
                    let watchpointReports = watchpointReportsModel.reports as ArrayFieldState<ModelState>;
                    let bv: ArrayFieldState<ModelState> = value.elements;
                    let findWatchpointReportById = (id) => watchpointReports.find(e => e.item.id === id);
                    let reportsValue = bv.filter(e => e.model == "watch").map(e => {
                        let id = e.item.id;
                        let watchpointReport = findWatchpointReportById(id); // TODO: these ids need to be made more unique or errors will occur
                        if(!watchpointReport) {
                            watchpointReport = {
                                item: newModelFromSchema(schema.models["watchpointReport"], { id }),
                                model: "watchpointReport"
                            };
                        }
            
                        return {
                            report: watchpointReport,
                            position: e.item.position as number
                        }
                    }).sort((e1, e2) => e1.position - e2.position).map(e => e.report);

                    store.dispatch(modelActions.updateModel({ name: "watchpointReports", value: {
                        reports: reportsValue
                    }}));
                }
            }
        }
        return next(action);
    }

    let shadowBeamlineSortingMiddleware: Middleware = store => next => action => {
        let sortValues = (v, vs) => v.sort((a, b) => {
            return parseFloat(vs(a.item.position)) - parseFloat(vs(b.item.position))
        });

        if(action.type === "models/updateModel") {
            let { name, value } = action.payload;
            if(name === "beamline") {
                let vs = getValueSelector(StoreTypes.Models)
                let v = vs(value.elements);
                let nv = sortValues(v, vs);

                let formBeamlineModel: ModelState = formSelectors.selectModel("beamline")(store.getState());
                if(formBeamlineModel !== undefined) {
                    let fvs = getValueSelector(StoreTypes.FormState);
                    console.log("fbm", formBeamlineModel);
                    store.dispatch(formActions.updateModel({
                        name,
                        value: {
                            ...formBeamlineModel,
                            elements: {
                                ...(formBeamlineModel.elements as any),
                                value: sortValues([...fvs(formBeamlineModel.elements as any)], fvs)
                            }
                        }
                    }))
                }
                

                return next(modelActions.updateModel({
                    name,
                    value: {
                        ...value,
                        elements: nv
                    }
                }));
            }
        }

        return next(action);
    }

    // TODO make server saving middleware


    const [modelsStore, _] = useState(() => configureStore({ 
        reducer: {
            [modelsSlice.name]: modelsSlice.reducer,
            [formStatesSlice.name]: formStatesSlice.reducer,
        },
        middleware: [
            shadowBeamlineWatchpointReportsMiddleware,
            shadowBeamlineSortingMiddleware
        ]
    }));

    return (
        <Provider store={modelsStore}>
            {props.children}
        </Provider>
    )
}

function SimulationInfoInitializer(props: { simulationId: string } & {[key: string]: any}) {
    let { simulationId } = props;

    

    let [simulationInfoPromise, updateSimulationInfoPromise] = useState(undefined);
    let [hasInit, updateHasInit] = useState(false);
    let appName = useContext(CAppName);
    let schema = useContext(CSchema);
    let routeHelper = useContext(CRouteHelper);
    let dispatch = useDispatch();

    useEffect(() => {
        updateSimulationInfoPromise(new Promise((resolve, reject) => {
            fetch(routeHelper.globalRoute("simulationData", {
                simulation_type: appName,
                simulation_id: simulationId,
                pretty: "0"
            })).then(async (resp) => {
                let simulationInfo = await resp.json();
                let models = simulationInfo['models'] as ModelState[];

                for(let [modelName, model] of Object.entries(models)) {
                    dispatch(modelActions.updateModel({
                        name: modelName,
                        value: model
                    }))
                }
                
                resolve({...simulationInfo, simulationId});
                updateHasInit(true);
            })
        }))
    }, [])

    let [handleFactory, _] = useCoupledState(schema, new BaseHandleFactory(schema))

    return hasInit && simulationInfoPromise && (
        <CHandleFactory.Provider value={handleFactory}>
            <CSimulationInfoPromise.Provider value={simulationInfoPromise}>
                {props.children}
            </CSimulationInfoPromise.Provider>
        </CHandleFactory.Provider>
    )
}

function SimulationCogMenu(props) {
    let appName = useContext(CAppName);
    let routeHelper = useContext(CRouteHelper);
    let navigate = useNavigate();
    let simulationInfoPromise = useContext(CSimulationInfoPromise);

    let [showCopyModal, updateShowCopyModal] = useState<boolean>(false);

    let [hasSimualtionInfo, simulationInfo] = useSetup(true, simulationInfoPromise);

    let deleteSimulationPromise = (simulationId: string) => {
        return fetch(routeHelper.globalRoute("deleteSimulation"), {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                simulationId,
                simulationType: appName
            })
        });
    }

    let discardChanges = async () => {
        let { simulationId, models: { simulation: { name }} } = simulationInfo || await simulationInfoPromise;
        await deleteSimulationPromise(simulationId);
        let newSimulationInfo: SimulationInfoRaw = await (await fetch(routeHelper.globalRoute("findByName", {
            simulation_type: appName,
            application_mode: "default", // TODO
            simulation_name: name as string
        }))).json();
        navigate(routeHelper.localRoute("source", {
            simulationId: newSimulationInfo.models.simulation.simulationId as string
        }));
    }

    let deleteSimulation = async () => {
        let { simulationId } = simulationInfo || await simulationInfoPromise;
        await deleteSimulationPromise(simulationId);
        navigate(routeHelper.localRoute("root"));
    }

    let exportArchive = async () => {
        let { simulationId, models: { simulation: { name }} } = simulationInfo || await simulationInfoPromise;
        window.open(routeHelper.globalRoute("exportArchive", {
            simulation_type: appName,
            simulation_id: simulationId,
            filename: `${name}.zip`
        }), "_blank")
    }

    let pythonSource = async () => {
        let { simulationId, models: { simulation: { name }} } = simulationInfo || await simulationInfoPromise;
        
        let r = await fetch(routeHelper.globalRoute("pythonSource2", { simulation_type: appName }), {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(
                {
                    simulationId: simulationId,
                    name: name
                }
            )
        })
        downloadAs(await r.blob(), getAttachmentFileName(r));

    }

    let openCopy = async (newName) => {
        let { simulationId, models: { simulation: { folder }} } = simulationInfo || await simulationInfoPromise;
        let { models: { simulation: { simulationId: newSimId }} } = await (await fetch(routeHelper.globalRoute("copySimulation"), {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                folder,
                name: newName,
                simulationId,
                simulationType: appName
            })
        })).json()
        navigate(routeHelper.localRoute("source", {
            simulationId: newSimId
        }));
    }

    return (
        <>
            <CopySimulationNamePickerModal
            show={showCopyModal}
            defaultName={simulationInfo ? `${simulationInfo.models.simulation.name} 2` : ""}
            onComplete={(name) => {
                updateShowCopyModal(false);
                openCopy(name)
            }}
            onCancel={() => updateShowCopyModal(false)}/>
            <NavToggleDropdown title={<FontAwesomeIcon icon={Icon.faCog}/>}>
                <Dropdown.Item onClick={() => exportArchive()}><FontAwesomeIcon icon={Icon.faCloudDownload}/> Export as ZIP</Dropdown.Item>
                <Dropdown.Item onClick={() => pythonSource()}><FontAwesomeIcon icon={Icon.faCloudDownload}/> Python Source</Dropdown.Item>
                <Dropdown.Item onClick={() => updateShowCopyModal(true)}><FontAwesomeIcon icon={Icon.faCopy}/> Open as a New Copy</Dropdown.Item>
                {
                    hasSimualtionInfo && (
                        simulationInfo.models.simulation.isExample ? (
                            <Dropdown.Item onClick={() => discardChanges()}><FontAwesomeIcon icon={Icon.faRepeat}/> Discard changes to example</Dropdown.Item>
                        ) : (
                            <Dropdown.Item onClick={() => deleteSimulation()}><FontAwesomeIcon icon={Icon.faTrash}/> Delete</Dropdown.Item>
                        )
                    )
                }
            </NavToggleDropdown>
        </>

    )
}

function CopySimulationNamePickerModal({show, defaultName, onComplete, onCancel}: {show: boolean, defaultName: string, onComplete: (string) => void, onCancel: () => void}) {
    let [name, updateName] = useState<string>(defaultName || "");

    return (
        <Modal show={show}>
            <Modal.Header>Copy Simulation</Modal.Header>
            <Modal.Body as={Container}>
                <Form.Group as={Row} className="mb-3">
                    <Form.Label column>
                        New Name
                    </Form.Label>
                    <Col>
                        <Form.Control onChange={(event) => updateName(event.target.value)} value={name}/>
                    </Col>
                </Form.Group>
                <Row>
                    <Col className="ms-auto col-auto">
                        <Button disabled={!name || name.length === 0} onClick={() => onComplete(name)}>Create Copy</Button>
                    </Col>
                    <Col className="col-auto">
                        <Button variant="danger" onClick={() => onCancel()}>Cancel</Button>
                    </Col>
                </Row>
            </Modal.Body>
        </Modal>
    )
}

function ReportEventManagerInitializer(props) {
    let routeHelper = useContext(CRouteHelper);

    return <CReportEventManager.Provider value={new ReportEventManager(routeHelper)}>
        {props.children}
    </CReportEventManager.Provider>
}

export function SimulationOuter(props) {

    let pathPrefix = useResolvedPath('');
    let currentRelativeRouter = new RelativeRouteHelper(pathPrefix);

    let handleFactory = useContext(CHandleFactory);
    let store = useStore();
    console.log("models", store.getState()[StoreTypes.Models.name]);
    let simNameHandle = handleFactory.createHandle(new Dependency("simulation.name"), StoreTypes.Models).hook();

    useEffect(() => {
        document.title = simNameHandle.value as string;
    })

    // TODO: navbar should route to home, when one is made
    return (
        <CRelativeRouterHelper.Provider value={currentRelativeRouter}>
            {props.children}
        </CRelativeRouterHelper.Provider>
    )

}

export function SimulationRoot(props: {simulationId: string}) {
    let { simulationId } = props;

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
        <SimulationStoreInitializer>
            
                <SimulationInfoInitializer simulationId={simulationId}>
                    <SimulationOuter>
                    <FormStateInitializer>
                        <ReportEventManagerInitializer>
                            <Portal targetId={NavbarRightContainerId} className="order-2">
                                <SimulationCogMenu/>
                            </Portal>
                            {layoutComponents}
                        </ReportEventManagerInitializer>
                    </FormStateInitializer>
                    </SimulationOuter>
                </SimulationInfoInitializer>
            
        </SimulationStoreInitializer>
    )
}
