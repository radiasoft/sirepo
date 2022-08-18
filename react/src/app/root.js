import { Routes, Route, useParams } from "react-router-dom";
import { ContextAppName } from "../components/context";

function AppWrapper(props) {
    let { appName } = useParams();

    return (
        <ContextAppName.Provider value={appName}>
            {props.children}
        </ContextAppName.Provider>
    )
}

export function RootRouter(props) {
    return (
        <Routes>
            <Route path="react/:appName/*" element={
                 <AppWrapper>
                    {props.children}
                </AppWrapper>
            }>
            </Route>
        </Routes>
    )
}