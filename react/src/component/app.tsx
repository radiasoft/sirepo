import React, { useContext, useEffect } from "react";
import { configureStore } from "@reduxjs/toolkit"
import { modelsSlice } from "../store/models";
import { formStatesSlice } from "../store/formState";
import { useSetup } from "../hook/setup";
import { Provider } from "react-redux";
import { SimulationBrowserRoot } from "./simbrowser";
import "./app.scss";
import { AppWrapper, CAppName, CSchema, CSimulationList } from "../data/appwrapper";
import { LoginRouter } from "./login";
import { SrNavbar } from "./reusable/navbar";
import { Container } from "react-bootstrap";

export const AppRoot = (props) => {
    const formStateStore = configureStore({
        reducer: {
            [modelsSlice.name]: modelsSlice.reducer,
            [formStatesSlice.name]: formStatesSlice.reducer,
        },
    });
    let appName = useContext(CAppName);
    let appWrapper = new AppWrapper(appName);

    useEffect(() => {
        if (appName) {
            document.title = `${appName.toUpperCase()} - Sirepo`;
        }
    }, [appName]);

    const [hasAppSchema, schema] = useSetup(true, appWrapper.getSchema());

    if(hasAppSchema) {
        return (
            <Provider store={formStateStore}>
                <CSchema.Provider value={schema}>
                    <SrNavbar title={appName.toUpperCase()} titleHref={'/'} simulationsHref={`/react/${appName}/simulations`}/>
                    <Container fluid className="app-body">
                        <LoginRouter>
                            <SimulationListInitializer>
                                <SimulationBrowserRoot/>
                            </SimulationListInitializer>
                        </LoginRouter>
                    </Container>
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
