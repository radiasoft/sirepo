import { useParams, Routes, Route } from "react-router-dom";
import { ContextAppName } from "../context";

function AppNameWrapper(props) {
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
                 <AppNameWrapper>
                    {props.children}
                </AppNameWrapper>
            }>
            </Route>
        </Routes>
    )
}
