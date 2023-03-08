import React from "react";
import { useContext } from "react";
import { Navigate } from "react-router";
import { CAppWrapper, CLoginStatus } from "../../data/appwrapper";
import { useSetup } from "../../hook/setup";
import { CRouteHelper } from "../../utility/route";
import { updateLoginStatusRef } from "./login";


export function LoginWithGuest(props) {
    let routeHelper = useContext(CRouteHelper);
    let appWrapper = useContext(CAppWrapper);
    let loginStatusRef = useContext(CLoginStatus);

    let [hasLoggedIn, _] = useSetup(true, appWrapper.doGuestLogin().then(() => updateLoginStatusRef(loginStatusRef, appWrapper)));

    if(hasLoggedIn) {
        console.log("redirecting to root because done with guest login");
    }
    return (
        hasLoggedIn && <Navigate to={routeHelper.localRoute('root')}/>
    )
}
