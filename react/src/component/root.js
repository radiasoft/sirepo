import { useParams, Routes, Route } from "react-router-dom";
import { CAppName } from "../data/appwrapper";
import React from "react";

function AppNameWrapper(props) {
    let { appName } = useParams();

    return (
        <CAppName.Provider value={appName}>
            {props.children}
        </CAppName.Provider>
    )
}

export function RootRouter(props) {
    return (
        <Routes>
            <Route path="react/:appName/*" element={
                 <AppNameWrapper>
                    {props.children}
                </AppNameWrapper>
            }>
            </Route>
        </Routes>
    )
}
