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
    let child = (
        <AppNameWrapper>
            {props.children}
        </AppNameWrapper>
    )

    return (
        <Routes>
            <Route path=":appName/*" element={child}/>
        </Routes>
    )
}
