import React, { useContext, useEffect } from "react";
import { useSetup } from "../hook/setup";
import { SimulationBrowserRoot } from "./simbrowser";
import "./app.scss";
import { AppWrapper, CAppName, CAppWrapper, CSchema, CSimulationList } from "../data/appwrapper";
import { LoginRouter } from "./login/login";
import { SrNavbar } from "./reusable/navbar";
import { Container } from "react-bootstrap";
import { CRouteHelper, RouteHelper } from "../utility/route";
import { getAppCombinedSchema } from "../utility/schema";

export const AppContextWrapper = (props) => {
    
    let appName = useContext(CAppName);
    const [hasAppSchema, schema] = useSetup(true, () => getAppCombinedSchema(appName));

    if(hasAppSchema) {
        const routeHelper = new RouteHelper(appName, schema);
        let appWrapper = new AppWrapper(appName, routeHelper);
        return (
            <CAppWrapper.Provider value={appWrapper}>
                <CSchema.Provider value={schema}>
                    <CRouteHelper.Provider value={routeHelper}>
                        {props.children}
                    </CRouteHelper.Provider>
                </CSchema.Provider>
            </CAppWrapper.Provider>
        )
    }
    return undefined;
}

export const AppComponent = (props) => {
    let appName = useContext(CAppName);
    let routeHelper = useContext(CRouteHelper);

    useEffect(() => {
        if (appName) {
            document.title = `${appName.toUpperCase()} - Sirepo`;
        }
    }, [appName]);

    return (
        <>
            <SrNavbar title={appName.toUpperCase()} titleHref={routeHelper.localRoute("root")} simulationsHref={routeHelper.localRoute("simulations")}/>
            <Container fluid className="app-body">
                <LoginRouter>
                    <SimulationListInitializer>
                        <SimulationBrowserRoot/>
                    </SimulationListInitializer>
                </LoginRouter>
            </Container>
        </>
    )
}

export const AppRoot = (props) => {
    return (
        <AppContextWrapper>
            <AppComponent/>
        </AppContextWrapper>
    )
}

export const SimulationListInitializer = (props) => {
    let appWrapper = useContext(CAppWrapper);

    const [hasSimulationList, simulationList] = useSetup(true, () => appWrapper.getSimulationList());
    return (
        <>
            {hasSimulationList && 
            <CSimulationList.Provider value={simulationList}>
                {props.children}
            </CSimulationList.Provider>}
        </>
    )
}
