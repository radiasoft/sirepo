import React, { useContext } from "react";
import { configureStore } from "@reduxjs/toolkit"
import { modelsSlice } from "../store/models";
import { formStatesSlice } from "../store/formState";
import { useSetup } from "../hook/setup";
import { Provider } from "react-redux";
import { SimulationBrowserRoot } from "./simbrowser";
import "./app.scss";
import { AppWrapper, CAppName, CSchema, CSimulationList } from "../data/appwrapper";
import { LoginRouter } from "./login";
import { Navigate } from "react-router";

export const AppRoot = (props) => {
    const formStateStore = configureStore({
        reducer: {
            [modelsSlice.name]: modelsSlice.reducer,
            [formStatesSlice.name]: formStatesSlice.reducer,
        },
    });
    let appName = useContext(CAppName);
    let appWrapper = new AppWrapper(appName);

    const [hasAppSchema, schema] = useSetup(true, appWrapper.getSchema());
    //const [hasMadeHomepageRequest] = useSetup(true, appWrapper.doGuestLogin());
    const [, loginStatus] = useSetup(true, appWrapper.getIsLoggedIn());

    if(hasAppSchema && loginStatus) {
        return (
            <Provider store={formStateStore}>
                <CSchema.Provider value={schema}>
                    <LoginRouter>
                        {
                            loginStatus.isLoggedIn ?
                            (
                                <SimulationListInitializer>
                                    <SimulationBrowserRoot/>
                                </SimulationListInitializer>
                            ) : (
                                <Navigate to={"/react/login"}/> // TODO @garsuga: abstract
                            )
                        }
                    </LoginRouter>
                </CSchema.Provider>
            </Provider>
        )
    }
    return undefined;
}

export const SimulationListInitializer = (props) => {
    let appName = useContext(CAppName);
    let appWrapper = new AppWrapper(appName);

    const [hasSimulationList, simulationList] = useSetup(true, appWrapper.getSimulationList());

    return (
        <>
            {hasSimulationList && 
            <CSimulationList.Provider value={simulationList}>
                {props.children}
            </CSimulationList.Provider>}
        </>
    )
}
