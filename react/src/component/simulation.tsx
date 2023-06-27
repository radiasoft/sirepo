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
    modelActions,
    ModelState,
    modelsSlice
} from "../store/models";
import { FormStateInitializer } from "./reusable/form";
import { useNavigate, useResolvedPath } from "react-router-dom";
import { CRelativeRouterHelper, CRouteHelper, RelativeRouteHelper } from "../utility/route";
import { ReportEventManager } from "../data/report";
import { CReportEventManager } from "../data/report";
import { CAppName, CSchema } from "../data/appwrapper";
import { LAYOUTS } from "../layout/layouts";
import { Dependency } from "../data/dependency";
import { NavbarRightContainerId, NavToggleDropdown } from "./reusable/navbar";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { useSetup } from "../hook/setup";
import { Portal } from "./reusable/portal";
import { downloadAs, getAttachmentFileName } from "../utility/download";
import { Provider, useDispatch, useStore } from "react-redux";
import { StoreState } from "../store/common";
import { configureStore } from "@reduxjs/toolkit";
import { formStatesSlice } from "../store/formState";
import { BaseHandleFactory, CHandleFactory } from "../data/handle";
import { StoreTypes } from "../data/data";
import { useCoupledState } from "../hook/coupling";
import { middlewaresForSchema } from "../data/middleware/middleware";
import { useSimulationInfo } from "../hook/simulationInfo";

export type SimulationInfoRaw = {
    models: StoreState<ModelState>,
    simulationType: string
} 

export type SimulationInfo = {
    simulationType: string,
    simulationId: string,
    version: string,
    name: string,
    isExample: boolean,
    folder: string
}

function SimulationInfoInitializer(props: { simulationId: string } & {[key: string]: any}) {
    let { simulationId } = props;

    let schema = useContext(CSchema);
    let appName = useContext(CAppName);
    let routeHelper = useContext(CRouteHelper);

    const [modelsStore, updateModelsStore] = useState(undefined);

    let [hasSimulationInfo, simulationInfo] = useSetup(true, () => new Promise((resolve, reject) => {
        fetch(routeHelper.globalRoute("simulationData", {
            simulation_type: appName,
            simulation_id: simulationId,
            pretty: "0"
        })).then(async (resp) => {
            let simulationInfo = {...(await resp.json()), simulationId} as SimulationInfoRaw;
            let models = simulationInfo['models'] as StoreState<ModelState>;

            let _store = configureStore({ 
                reducer: {
                    [modelsSlice.name]: modelsSlice.reducer,
                    [formStatesSlice.name]: formStatesSlice.reducer,
                },
                middleware: [...middlewaresForSchema(schema, simulationInfo)]
            })

            updateModelsStore(_store)

            for(let [modelName, model] of Object.entries(models)) {
                _store.dispatch(modelActions.updateModel({
                    name: modelName,
                    value: model
                }))
            }

            _store.dispatch(modelActions.updateModel({
                name: "simulation",
                value: {
                    ...models["simulation"],
                    ...{
                        ...simulationInfo,
                        models: undefined
                    }
                }
            }))

            console.log("store", _store.getState());
            
            resolve(simulationInfo);
        })
    }));

    let [handleFactory, _] = useCoupledState(schema, new BaseHandleFactory(schema))

    return hasSimulationInfo && (
        <Provider store={modelsStore}>
            <CHandleFactory.Provider value={handleFactory}>
                {props.children}
            </CHandleFactory.Provider>
        </Provider>
    )
}

function SimulationCogMenu(props) {
    let appName = useContext(CAppName);
    let routeHelper = useContext(CRouteHelper);
    let navigate = useNavigate();
    let schema = useContext(CSchema);
    let handleFactory = useContext(CHandleFactory);

    let [showCopyModal, updateShowCopyModal] = useState<boolean>(false);

    let simulationInfo = useSimulationInfo(handleFactory);

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
        let { simulationId, name } = simulationInfo;
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
        let { simulationId } = simulationInfo;
        await deleteSimulationPromise(simulationId);
        navigate(routeHelper.localRoute("root"));
    }

    let exportArchive = async () => {
        let { simulationId, name } = simulationInfo;
        window.open(routeHelper.globalRoute("exportArchive", {
            simulation_type: appName,
            simulation_id: simulationId,
            filename: `${name}.zip`
        }), "_blank")
    }

    let pythonSource = async () => {
        let { simulationId, name } = simulationInfo;

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
        let { simulationId, folder } = simulationInfo;
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
            defaultName={simulationInfo ? `${simulationInfo.name} 2` : ""}
            onComplete={(name) => {
                updateShowCopyModal(false);
                openCopy(name)
            }}
            onCancel={() => updateShowCopyModal(false)}/>
            <NavToggleDropdown title={<FontAwesomeIcon icon={Icon.faCog}/>}>
                <Dropdown.Item onClick={() => exportArchive()}><FontAwesomeIcon icon={Icon.faCloudDownload}/> Export as ZIP</Dropdown.Item>
                <Dropdown.Item onClick={() => pythonSource()}><FontAwesomeIcon icon={Icon.faCloudDownload}/> { schema.constants.simSourceDownloadText }</Dropdown.Item>
                <Dropdown.Item onClick={() => updateShowCopyModal(true)}><FontAwesomeIcon icon={Icon.faCopy}/> Open as a New Copy</Dropdown.Item>
                {
                    (
                        simulationInfo.isExample ? (
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

    return (
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
    )
}
