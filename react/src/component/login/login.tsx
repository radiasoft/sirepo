import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import React, { useContext, useEffect, useState } from "react"
import { Button, Col, Container, Dropdown, Form, Image, Nav, Row } from "react-bootstrap"
import { Navigate, Route, Routes, useNavigate, useParams } from "react-router"
import { AuthMethod, CAppName, CAppWrapper, CLoginStatus, CSchema } from "../../data/appwrapper"
import { useSetup } from "../../hook/setup"
import { NavbarRightContainerId, NavToggleDropdown } from "../reusable/navbar";
import { Portal } from "../reusable/portal";
import "./login.scss";
import { LoginEmailConfirm, LoginWithEmail } from "./email";
import { CRouteHelper } from "../../utility/route";

export const LoginRouter = (props) => {
    let appWrapper = useContext(CAppWrapper);
    let routeHelper = useContext(CRouteHelper);
    const [hasLoginStatus, loginStatus] = useSetup(true, appWrapper.getLoginStatus());

    return hasLoginStatus && (
        <CLoginStatus.Provider value={loginStatus}>
            <Portal targetId={NavbarRightContainerId} className="order-3">
                <NavbarSlack/>
            </Portal>
            <Portal targetId={NavbarRightContainerId} className="order-5 sr-navbar-auth">
                <NavbarAuthStatus/>
            </Portal>
            <Routes>
                <Route path={`${routeHelper.localRoute("logout")}/*`} element={<LogoutRoot/>}/>
                <Route path={`${routeHelper.localRoute("login")}/*`} element={<LoginRoot/>}/>
                <Route path={routeHelper.localRoute("loginConfirm")} element={<LoginConfirm/>}/>
                <Route path="*" element={<CatchLoggedOut>{props.children}</CatchLoggedOut>}/>
            </Routes>
        </CLoginStatus.Provider>
    )
}

export const NavbarSlack = (props) => {
    let loginStatus = useContext(CLoginStatus);

    return (
        <>
        {
            loginStatus.slackUri && (
                <Nav.Link href={loginStatus.slackUri}><img style={{"filter": "invert(0.5)"}} width="70" src="/static/svg/slack.svg" title="Join us on Slack"/></Nav.Link>
            )
        }
        </>
    )
}

export const NavbarAuthStatus = (props) => {
    let loginStatus = useContext(CLoginStatus);
    let schema = useContext(CSchema);
    let appWrapper = useContext(CAppWrapper);
    let routeHelper = useContext(CRouteHelper);

    if(loginStatus.method === "guest") {
        return (<></>)
    }

    if(loginStatus.isLoggedIn) {
        return (
            <NavToggleDropdown title={
                <>{
                    loginStatus.avatarUrl ? (
                        <Image className="sr-login-avatar" src={loginStatus.avatarUrl} fluid rounded={true}/>
                    ) : (
                        <FontAwesomeIcon icon={Icon.faPerson}/>
                    )
                }</>
            }>
                {
                    loginStatus.displayName && loginStatus.displayName.length > 0 && (
                        <Dropdown.Header>{loginStatus.displayName}</Dropdown.Header>
                    )
                }
                {
                    loginStatus.paymentPlan && (
                        <Dropdown.Header>{appWrapper.getPaymentPlanName(loginStatus.paymentPlan, schema)}</Dropdown.Header>
                    )
                }
                {
                    loginStatus.userName && (
                        <Dropdown.Header>{loginStatus.userName}</Dropdown.Header>
                    )
                }
                <Dropdown.Item href={routeHelper.localRoute("logout")}>Sign Out</Dropdown.Item>
            </NavToggleDropdown>
        )
    }

    return (
        <Nav.Link href={routeHelper.localRoute("login")}>Sign In</Nav.Link>
    )


}

export const CatchLoggedOut = (props) => {
    let routeHelper = useContext(CRouteHelper);
    let loginStatus = useContext(CLoginStatus);

    return (
        <>
            {
                (loginStatus.isLoggedIn && !loginStatus.needCompleteRegistration) || loginStatus.method === "guest" ?
                (
                    props.children
                ) : (
                    <Navigate to={routeHelper.localRoute("login")}/> // TODO @garsuga: abstract
                )
            }
        </>
    )
}

type LoginConfirmParams = {
    token: string,
    method: AuthMethod,
    needCompleteRegistration: "0" | "1"
}

export const LoginConfirm = (props) => {
    let { token, method, needCompleteRegistration } = useParams<LoginConfirmParams>();

    switch(method) {
        case 'email':
            return <LoginEmailConfirm needCompleteRegistration={needCompleteRegistration} token={token}/>
        default:
            throw new Error(`could not handle login method=${method}`)
    }
}



export const LoginNeedCompleteRegistration = (props) => {
    let appName = useContext(CAppName);
    let routeHelper = useContext(CRouteHelper);
    let navigate = useNavigate();
    let onCompleteForm = (data: {[key: string]: any}) => {
        fetch(routeHelper.globalRoute("authCompleteRegistration"), {
            method: "POST",
            body: JSON.stringify({ ...data, simulationType: appName }),
            headers: {
                "Content-Type": "application/json"
            }
        }).then(() => navigate(routeHelper.localRoute("root")))
    }
    return (
        <LoginExtraInfoForm onComplete={(data) => onCompleteForm(data)}/>
    )
}

export const LoginExtraInfoForm = (props: { onComplete: ({displayName}) => void }) => {
    let { onComplete } = props;
    let [displayName, updateDisplayName] = useState<string>("");
    return (
        <>
            <p>Please enter your full name to complete your Sirepo registration.</p>
            <Form.Group as={Row} className="mb-3" controlId="formPlaintextEmail">
                <Form.Label column sm="3">
                    Your full name
                </Form.Label>
                <Col sm="9">
                    <Form.Control value={displayName} onChange={(e) => updateDisplayName(e.target.value)}/>
                </Col>
            </Form.Group>
            <Button variant="primary" onClick={() => onComplete({ displayName })}>Continue</Button>
        </>
    )
}

export const LoginRoot = (props) => {
    let loginStatus = useContext(CLoginStatus);
    let routeHelper = useContext(CRouteHelper);

    let getLoginComponent = (method: string): JSX.Element => {
        switch(method) {
            case "email":
                return <LoginWithEmail/>
            case "guest":
                return <Navigate to={routeHelper.localRoute("root")}/>
            default:
                throw new Error(`could not handle login method=${method}`)
        }
    }

    if(loginStatus.needCompleteRegistration) {
        return (
            <Container className="sm-12 lg-6">
                <LoginNeedCompleteRegistration/>
            </Container>

        )
    }

    if(loginStatus.isLoggedIn && !loginStatus.needCompleteRegistration) {
        return (
            <Navigate to={routeHelper.localRoute("root")}></Navigate>
        )
    }

    return (
        <Container className="sm-12 lg-6">
            {getLoginComponent(loginStatus.visibleMethod)}
        </Container>
    )
}

export function LogoutRoot(props) {
    let navigate = useNavigate();
    let appName = useContext(CAppName);
    let routeHelper = useContext(CRouteHelper);
    useEffect(() => {
        fetch(routeHelper.globalRoute("authLogout", { simulation_type: appName })).then(() => navigate(routeHelper.localRoute("root")));
    })


    return <>Signing out...</>
}
