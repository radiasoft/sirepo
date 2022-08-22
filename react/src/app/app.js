// import {React}
import React, { useContext, useEffect, useRef, useState } from "react";
import { Button, Col } from "react-bootstrap";
import { configureStore } from "@reduxjs/toolkit";
import { useDispatch, Provider, useSelector, useStore } from "react-redux";
import { useSetup } from "../hooks";
import {
    modelsSlice,
    selectModel,
    updateModel,
    selectModels,
} from "../models";
import {
    selectFormState,
    updateFormState,
    updateFormFieldState,
    formStatesSlice
} from '../formState'
import "./app.scss"
import Schema from './schema'
import { Graph2dFromApi } from "../components/graph2d";
import { SchemaEditorPanel } from "../components/form";
import { 
    ContextAppInfo,
    ContextAppName,
    ContextAppViewBuilder,
    ContextReduxFormActions, 
    ContextReduxFormSelectors, 
    ContextReduxModelActions, 
    ContextReduxModelSelectors, 
    ContextSimulationInfoPromise, 
    ContextSimulationListPromise 
} from '../components/context'
import { Panel } from "../components/panel";
import { SimulationBrowserRoot } from "./simbrowser";

function pollRunSimulation({ appName, models, simulationId, report, pollInterval}) {
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
                    //setTimeout(doFetch, pollInterval); // TODO
                } else {
                    reject();
                }
            })
        }
        doFetch();
    })
}



function SimulationListInitializer(child) {
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

function SimulationVisualWrapper(visualName, title, visualComponent, passedProps) {
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

function AppViewBuilderWrapper(child) {
    let ChildComponent = child;
    return (props) => {
        let contextFn = useContext;
        let appInfo = contextFn(ContextAppInfo);
        let viewBuilder = new AppViewBuilder(appInfo);
        return (
            <ContextAppViewBuilder.Provider value={viewBuilder}>
                <ChildComponent {...props}/>
            </ContextAppViewBuilder.Provider>
        )
    }  
}

function AppInfoWrapper(appInfo) {
    return (child) => {
        let ChildComponent = child;
        return (props) => {
            return (
                <ContextAppInfo.Provider value={appInfo}>
                    <ChildComponent {...props}/>
                </ContextAppInfo.Provider>
            )
        }
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
    let appInfo = {schema};

    return ReduxConstantsWrapper(
        AppInfoWrapper(appInfo)(
            AppViewBuilderWrapper(
                SimulationListInitializer(
                    () => {
                        return (
                            <SimulationBrowserRoot/>
                        )
                    }
                )
            )
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

    let appName = useContext(ContextAppName);

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
            <Provider store={formStateStore}>
                <AppChild></AppChild>
            </Provider>
        )
    }
}

export default AppRoot;
