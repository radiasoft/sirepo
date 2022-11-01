import { useState, useEffect, useContext } from "react";
import {
    ContextAppName,
    ContextSimulationListPromise,
    ContextSchema,
    ContextLayouts
} from "../context"
import { configureStore } from "@reduxjs/toolkit"
import { modelsSlice } from "../store/models";
import { formStatesSlice } from "../store/formState";
import { useSetup } from "../hook/setup";
import { compileSchemaFromJson, mergeSchemaJson } from "../utility/schema";
import { Provider } from "react-redux";
import { SimulationBrowserRoot } from "../component/simbrowser";
import { Layouts } from "../layout/layouts";
import "./app.scss";

function SimulationListInitializer(props) {
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
                let simulationList = await resp.json();
                resolve(simulationList);
            })
        }))
    }, [])

    return simulationListPromise && (
        <ContextSimulationListPromise.Provider value={simulationListPromise}>
            {props.children}
        </ContextSimulationListPromise.Provider>
    )
}

export const AppRoot = (props) => {
    const [schema, updateSchema] = useState(undefined);
    const formStateStore = configureStore({
        reducer: {
            [modelsSlice.name]: modelsSlice.reducer,
            [formStatesSlice.name]: formStatesSlice.reducer,
        },
    });

    let appName = useContext(ContextAppName);

    

    const hasAppSchema = useSetup(true,
        (finishInitSchema) => {
            Promise.all([
                fetch(`/static/react-json/common-schema.json`),
                fetch(`/static/react-json/${appName}-schema.json`)
            ]).then(([commonResp, appResp]) => {
                Promise.all([
                    commonResp.json(), 
                    appResp.json()
                ]).then(([commonJson, appJson]) => {
                    let schemaJson = mergeSchemaJson(commonJson, appJson)
                    updateSchema(compileSchemaFromJson(schemaJson));
                    finishInitSchema();
                })
            })

            /*fetch(`/static/react-json/${appName}-schema.json`).then(resp => {
                resp.json().then(json => {
                    updateSchema(compileSchemaFromJson(json));
                    finishInitSchema();
                })
            })*/
        }
    )

    const hasMadeHomepageRequest = useSetup(true,
        (finishHomepageRequest) => {
            fetch(`/auth-guest-login/${appName}`).then(() => {
                finishHomepageRequest();
            });
        }
    )

    if(hasAppSchema && hasMadeHomepageRequest) {
        //let AppChild = buildAppComponentsRoot(schema);
        return (
            <Provider store={formStateStore}>
                <ContextSchema.Provider value={schema}>
                    <ContextLayouts.Provider value={new Layouts()}>
                        <SimulationListInitializer>
                            <SimulationBrowserRoot></SimulationBrowserRoot>
                        </SimulationListInitializer>
                    </ContextLayouts.Provider>
                </ContextSchema.Provider>
            </Provider>
        )
    }
}
