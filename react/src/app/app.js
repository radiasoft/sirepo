// import {React}
import React, { useContext, useEffect, useState } from "react";
import { configureStore } from "@reduxjs/toolkit";
import { Provider } from "react-redux";
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
import { compileSchemaFromJson } from '../schema'
import { ViewLayoutsPanel } from "../components/panel";
import { 
    ContextAppInfo,
    ContextAppName,
    ContextAppViewBuilder,
    ContextReduxFormActions, 
    ContextReduxFormSelectors, 
    ContextReduxModelActions, 
    ContextReduxModelSelectors,  
    ContextSimulationListPromise 
} from '../components/context'
import { SimulationBrowserRoot } from "./simbrowser";

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
    console.log("appInfo", appInfo);
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
            'panel': ViewLayoutsPanel(appInfo)
            //'graph2d': (viewInfo) => SimulationVisualWrapper(viewInfo.viewName, viewInfo.view.title, Graph2dFromApi, { width: '100%', height: '100%' })
        }
    }

    buildComponentForView = (viewInfo) => {
        let componentBuilder = this.components[viewInfo.view.type || 'panel'];

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
            //updateSchema(Schema);
            console.log("fetching schema");
            fetch(`/react/schema/${appName}.json`).then(resp => {
                console.log("fetched schema");
                resp.json().then(json => {
                    console.log("converted schema to json");
                    updateSchema(compileSchemaFromJson(json));
                    finishInitSchema();
                })
            })
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
