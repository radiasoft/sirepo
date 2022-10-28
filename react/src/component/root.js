import { useParams, Routes, Route, Navigate } from "react-router-dom";
import { ContextAppName } from "../context";

function AppNameWrapper(props) {
    let { appName } = useParams();

    return (
        <ContextAppName.Provider value={appName}>
            {props.children}
        </ContextAppName.Provider>
    )
}

function ReactRerouteComponent(props) {
    let { appName } = useParams();

    return <Navigate to={`/react/${appName}`}></Navigate>
}

export function RootRouter(props) {
    return (
        <Routes>
            <Route path="react">
                <Route path=":appName/*" element={
                    <AppNameWrapper>
                        {props.children}
                    </AppNameWrapper>
                }>
                </Route>
            </Route>
            <Route path=":appName" element={<ReactRerouteComponent/>}>
            </Route>
        </Routes>
    )
}
