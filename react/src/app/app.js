// import {React}
import React, { useContext, useEffect, useRef, useState } from "react";
import { Button, Col } from "react-bootstrap";
import { configureStore } from "@reduxjs/toolkit";
import { useDispatch, Provider, useSelector, useStore } from "react-redux";
import { useSetup } from "../hooks";
import {
    modelsSlice,
    selectModel,
    loadModelData,
    selectIsLoaded,
    updateModel,
    selectModels,
} from "../models";
import { mapProperties } from '../helper'
import {
    selectFormState,
    updateFormState,
    updateFormFieldState,
    formStatesSlice
} from '../formState'
import "./app.scss"
import { ViewGrid } from "../components/simulation";
import Schema from './schema'
import { Graph2dFromApi } from "../components/graph2d";
import { SchemaEditorPanel, FormStateInitializer } from "../components/form";
import { 
    ContextAppName,
    ContextReduxFormActions, 
    ContextReduxFormSelectors, 
    ContextReduxModelActions, 
    ContextReduxModelSelectors, 
    ContextSimulationInfoPromise, 
    ContextSimulationListPromise 
} from '../components/context'
import { Panel } from "../components/panel";

const pollRunSimulation = ({ appName, models, simulationId, report, pollInterval}) => {
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
                console.log("polled simulation: " + state);
                if(state == 'completed') {
                    resolve(simulationStatus);
                } else if (state == 'pending') {
                    //setTimeout(doFetch, pollInterval);
                } else {
                    reject();
                }
            })
        }
        doFetch();
    })
}

const SimulationInfoInitializer = (child) => {
    return (props) => {
        let contextFn = useContext;
        let stateFn = useState;
        let effectFn = useEffect;
        let dispatchFn = useDispatch;

        let simulationListPromise = contextFn(ContextSimulationListPromise);
        let { updateModel } = contextFn(ContextReduxModelActions);
        let [simulationInfoPromise, updateSimulationInfoPromise] = stateFn(undefined);
        let [hasInit, updateHasInit] = stateFn(false);
        let appName = contextFn(ContextAppName);
        let dispatch = dispatchFn();

        effectFn(() => {
            updateSimulationInfoPromise(new Promise((resolve, reject) => {
                simulationListPromise.then(simulationList => {
                    let simulation = simulationList[0];
                    let { simulationId } = simulation;
                    fetch(`/simulation/${appName}/${simulationId}/0/source`).then(async (resp) => {
                        let simulationInfo = await resp.json();
                        let { models } = simulationInfo;
                        console.log("retrieved simulation info", simulationInfo);
                        // TODO: use models

                        for(let [modelName, model] of Object.entries(models)) {
                            dispatch(updateModel({
                                name: modelName,
                                value: model
                            }));
                        }

                        resolve({...simulationInfo, simulationId});
                        updateHasInit(true);
                    })
                })
            }))
        }, [])

        let ChildComponent = child;
        return hasInit && simulationInfoPromise && (
            <ContextSimulationInfoPromise.Provider value={simulationInfoPromise}>
                <ChildComponent {...props}>

                </ChildComponent>
            </ContextSimulationInfoPromise.Provider>
        )
    }
}

const SimulationListInitializer = (child) => {
    return (props) => {
        let stateFn = useState;
        let effectFn = useEffect;
        let contextFn = useContext;

        let [simulationListPromise, updateSimulationListPromise] = stateFn(undefined)
        let appName = contextFn(ContextAppName);

        effectFn(() => {
            updateSimulationListPromise(new Promise((resolve, reject) => {
                fetch('/simulation-list', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        simulationType: appName
                    })
                }).then(async (resp) => {
                    console.log("retrieved simulation list");
                    let simulationList = await resp.json();
                    resolve(simulationList);
                })
            }))
        }, [])

        let ChildComponent = child;
        return simulationListPromise && (
            <ContextSimulationListPromise.Provider value={simulationListPromise}>
                <ChildComponent {...props}>

                </ChildComponent>
            </ContextSimulationListPromise.Provider>
        )
    }
}

const MissingComponentPlaceholder = (props) => {
    return (
        <div>
            Missing Component Builder!
        </div>
    )
}

let SimulationVisualWrapper = (visualName, title, visualComponent, passedProps) => {
    return (props) => {
        let contextFn = useContext;
        let stateFn = useState;
        let effectFn = useEffect;

        let simulationInfoPromise = contextFn(ContextSimulationInfoPromise);
        let appName = contextFn(ContextAppName);

        let [simulationData, updateSimulationData] = stateFn(undefined);

        effectFn(() => {
            let simulationDataPromise= new Promise((resolve, reject) => {
                simulationInfoPromise.then(({ models, simulationId, simulationType, version }) => {
                    console.log("starting to poll simulation");
                    pollRunSimulation({
                        appName,
                        models,
                        simulationId,
                        report: visualName,
                        pollInterval: 500
                    }).then((simulationData) => {
                        console.log("finished polling simulation");
                        resolve(simulationData);
                    })
                })
            });
    
            simulationDataPromise.then(updateSimulationData);
        }, [])

        

        let VisualComponent = simulationData ? visualComponent(simulationData) : undefined;

        return (
            <Panel title={title} panelBodyShown={true}>
                {VisualComponent && <VisualComponent {...props} {...passedProps}></VisualComponent>}
            </Panel>
        )
    }
}

class AppViewBuilder{
    constructor (appInfo) { 
        this.components = {
            'editor': SchemaEditorPanel(appInfo),
            'graph2d': (viewInfo) => SimulationVisualWrapper(viewInfo.viewName, viewInfo.view.title, Graph2dFromApi, { width: '100%', height: '100%' })
        }
    }

    buildComponentForView = (viewInfo) => {
        let componentBuilder = this.components[viewInfo.view.type || 'editor'];

        if(!componentBuilder) {
            return MissingComponentPlaceholder;
        }

        return componentBuilder(viewInfo);
    }
}

function LoadDataButton(props) {
    let dispatch = useDispatch();
    return (
        <Col className="mt-3 ms-3">
            <Button onClick={() => dispatch(loadModelData())}>Load Data</Button>
        </Col>
    )
}

let ReduxConstantsWrapper = (child) => {
    return (props) => {
        let ChildComponent = child;

        return (
            <ContextReduxModelActions.Provider value={{updateModel}}>
                <ContextReduxModelSelectors.Provider value={{selectModel, selectModels}}>
                    <ContextReduxFormActions.Provider value={{updateFormFieldState, updateFormState}}>
                        <ContextReduxFormSelectors.Provider value={{selectFormState}}>
                            <ChildComponent {...props}></ChildComponent>
                        </ContextReduxFormSelectors.Provider>
                    </ContextReduxFormActions.Provider>
                </ContextReduxModelSelectors.Provider>
            </ContextReduxModelActions.Provider>
        )
    }
}

function buildAppComponentsRoot(schema) {
    let viewInfos = mapProperties(schema.views, (viewName, view) => {
        return {
            view,
            viewName: viewName
        }
    })

    let viewBuilder = new AppViewBuilder({ schema });
    
    let viewComponents = mapProperties(viewInfos, (viewName, viewInfo) => viewBuilder.buildComponentForView(viewInfo));

    const RequiresIsLoaded = (componentIf, componentElse) => (props) => {
        let selectorFn = useSelector;
        let isLoaded = selectorFn(selectIsLoaded);
        let ChildComponent = isLoaded ? componentIf : componentElse;
        return (<>
            {ChildComponent && <ChildComponent {...props}></ChildComponent>}
        </>)
    }

    return ReduxConstantsWrapper(
        RequiresIsLoaded(
            SimulationListInitializer(
                SimulationInfoInitializer(
                    FormStateInitializer({ viewInfos, schema })(
                        () => {
                            return (
                                <ViewGrid views={Object.values(viewComponents)}>
                                </ViewGrid>
                            )
                        }
                    )
                )
            ),
            LoadDataButton
        )
    )
}


const AppRoot = (props) => {
    const [schema, updateSchema] = useState(undefined);
    const formStateStore = configureStore({
        reducer: {
            [modelsSlice.name]: modelsSlice.reducer,
            [formStatesSlice.name]: formStatesSlice.reducer,
        },
    });

    let { appName } = props;

    const hasSchema = useSetup(true,
        (finishInitSchema) => {
            updateSchema(Schema);
            finishInitSchema();
        }
    )

    const hasMadeHomepageRequest = useSetup(true,
        (finishHomepageRequest) => {
            fetch(`/auth-guest-login/${appName}`).then(() => {
                finishHomepageRequest();
            });
        }
    )

    if(hasSchema && hasMadeHomepageRequest) {
        let AppChild = buildAppComponentsRoot(schema);
        return (
            <ContextAppName.Provider value={appName}>
                <Provider store={formStateStore}>
                    <AppChild></AppChild>
                </Provider>
            </ContextAppName.Provider>
        )
    }
}

export default AppRoot;
