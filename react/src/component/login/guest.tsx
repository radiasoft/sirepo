import React from "react";
import { useContext } from "react";
import { Navigate } from "react-router";
import { CAppWrapper, CLoginStatusRef } from "../../data/appwrapper";
import { useSetup } from "../../hook/setup";
import { CRouteHelper } from "../../utility/route";
import { updateLoginStatusRef } from "./login";


export function LoginWithGuest(props) {
    let routeHelper = useContext(CRouteHelper);
    let appWrapper = useContext(CAppWrapper);
    let loginStatusRef = useContext(CLoginStatusRef);

    let [hasLoggedIn, _] = useSetup(true, () => appWrapper.doGuestLogin().then(() => updateLoginStatusRef(loginStatusRef, appWrapper)));

    return (
        hasLoggedIn && <Navigate to={routeHelper.localRoute('root')}/>
    )
}
