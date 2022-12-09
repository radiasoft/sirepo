import React, { useContext } from "react";
import { configureStore } from "@reduxjs/toolkit"
import { modelsSlice } from "../store/models";
import { formStatesSlice } from "../store/formState";
import { useSetup } from "../hook/setup";
import { Provider } from "react-redux";
import { SimulationBrowserRoot } from "./simbrowser";
import "./app.scss";
import { AppWrapper, CAppName, CSchema, CSimulationList } from "../data/appwrapper";

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
    

    if(hasAppSchema && hasMadeHomepageRequest && hasSimulationList) {
        return (
            <Provider store={formStateStore}>
                <CSchema.Provider value={schema}>
                    <CSimulationList.Provider value={simulationList}>
                        <SimulationBrowserRoot></SimulationBrowserRoot>
                    </CSimulationList.Provider>
                </CSchema.Provider>
            </Provider>
        )
    }
}

export const SimulationListInitializer = (props) => {
    const [hasSimulationList, simulationList] = useSetup(hasMadeHomepageRequest, appWrapper.getSimulationList());
}
