import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import React, { MutableRefObject, useContext, useEffect, useRef, useState } from "react"
import { Button, Col, Container, Dropdown, Form, Image, Nav, Row, Modal } from "react-bootstrap"
import { Navigate, Route, Routes, useNavigate, useParams } from "react-router"
import { AppWrapper, AuthMethod, CAppName, CAppWrapper, CLoginStatusRef, CSchema, LoginStatus } from "../../data/appwrapper"
import { useSetup } from "../../hook/setup"
import { NavbarRightContainerId, NavToggleDropdown } from "../reusable/navbar";
import { Portal } from "../reusable/portal";
import "./login.scss";
import { LoginEmailConfirm, LoginWithEmail } from "./email";
import { CRouteHelper } from "../../utility/route";
import { LoginWithGuest } from "./guest";
import { useLocation } from "react-router-dom";

export async function updateLoginStatusRef(ref: MutableRefObject<LoginStatus>, appWrapper: AppWrapper) {
    let status = await appWrapper.getLoginStatus();
    ref.current = status;
}

export const LoginRouter = (props) => {
    let appWrapper = useContext(CAppWrapper);
    let routeHelper = useContext(CRouteHelper);
    let loginStatusRef = useRef(undefined);
    let location = useLocation();
    const [hasLoginStatus, _] = useSetup(true, () => updateLoginStatusRef(loginStatusRef, appWrapper));
    const isSimulations = location.pathname.startsWith(routeHelper.localRoute("simulations"));

    return hasLoginStatus && (
        <CLoginStatusRef.Provider value={loginStatusRef}>
            { isSimulations &&
              <Portal targetId={NavbarRightContainerId} className="order-1 navbar-nav">
                  <NavbarNewSimulation/>
              </Portal>
            }
            <Portal targetId={NavbarRightContainerId} className="order-3 navbar-nav">
                <NavbarSlack/>
            </Portal>
            <Portal targetId={NavbarRightContainerId} className="order-5 navbar-nav">
                <NavbarAuthStatus/>
            </Portal>
            <Routes>
                <Route path={`${routeHelper.localRoutePattern("logout")}/*`} element={<LogoutRoot/>}/>
                <Route path={`${routeHelper.localRoutePattern("login")}/*`} element={<LoginRoot/>}/>
                <Route path={routeHelper.localRoutePattern("loginWithEmailConfirm")} element={<LoginConfirm/>}/>
                <Route path="*" element={<CatchLoggedOut>{props.children}</CatchLoggedOut>}/>
            </Routes>
        </CLoginStatusRef.Provider>
    )
}

export const NavbarNewSimulation = (props) => {
    const appName = useContext(CAppName);
    const routeHelper = useContext(CRouteHelper);
    const [modalShown, updateModalShown] = useState(false);
    const [name, updateName] = useState<string>("");
    const navigate = useNavigate();
    const location = useLocation();
    const _cancel = () => {
        updateName('');
        updateModalShown(false);
    };
    const onComplete = (data: { [key: string]: any }) => {
        const folder = location.pathname.replace(/^.*?\/simulations/, '');
        fetch(routeHelper.globalRoute("newSimulation"), {
            method: "POST",
            body: JSON.stringify({ ...data, simulationType: appName, folder: folder || '/' }),
            headers: {
                "Content-Type": "application/json",
            },
        }).then(response => response.json())
        .then(data => {
            //TODO(pjm): source is hardcoded and should be default route from schema
            const path = routeHelper.localRoute("source", {
                simulationId: data.models.simulation.simulationId
            });
            updateName('');
            navigate(path);
        });
    }
    const validateSimName = (value) => {
        const invalidCharacters = /[\\/|&:+?'*"<>]/;
        updateName(value.replace(/^\s+/, '').replace(invalidCharacters, ''));
    }
    return (
        <>
        <Nav.Link
            onClick={() => updateModalShown(true)}
        >New Simulation</Nav.Link>
        <Modal show={modalShown} onHide={() => _cancel()} size="lg">
            <Modal.Header className="lead bg-info bg-opacity-25">
                New Simulation
            </Modal.Header>
            <Modal.Body>
            <Form.Group as={Row} className="mb-3">
                <Form.Label className="text-end" column sm="5">
                    Name
                </Form.Label>
                <Col sm="7">
                    <Form.Control autoFocus size="sm" value={name} onChange={(e) => validateSimName(e.target.value)}/>
                </Col>
            </Form.Group>
            { name && <div className="text-center sr-form-action-buttons">
                <Button variant="primary" onClick={() => onComplete({ name })}>Save Changes</Button>
                <Button className="ms-1" variant="light" onClick={() => _cancel()}>Cancel</Button>
            </div>}
            </Modal.Body>
        </Modal>
        </>
    )
}

export const NavbarSlack = (props) => {
    let loginStatus = useContext(CLoginStatusRef).current;

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
    let loginStatus = useContext(CLoginStatusRef).current;
    let schema = useContext(CSchema);
    let appWrapper = useContext(CAppWrapper);
    let routeHelper = useContext(CRouteHelper);

    if(loginStatus.visibleMethod === "guest") {
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
    let loginStatus = useContext(CLoginStatusRef).current;
    return (
        <>
            {
                (loginStatus.isLoggedIn && !loginStatus.needCompleteRegistration) ?
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
    needCompleteRegistration: "0" | "1"
}

export const LoginConfirm = (props) => {
    let { token, needCompleteRegistration } = useParams<LoginConfirmParams>();
    return <LoginEmailConfirm needCompleteRegistration={needCompleteRegistration} token={token}/>
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
                <Col sm="7">
                    <Form.Control value={displayName} onChange={(e) => updateDisplayName(e.target.value)}/>
                </Col>
                <Col sm="2">
                    <Button variant="primary" onClick={() => onComplete({ displayName })} disabled={! displayName}>Continue</Button>
                </Col>
            </Form.Group>
        </>
    )
}

export const LoginRoot = (props) => {
    let loginStatus = useContext(CLoginStatusRef).current;
    let routeHelper = useContext(CRouteHelper);

    let getLoginComponent = (method: string): JSX.Element => {
        switch(method) {
            case "email":
                return <LoginWithEmail/>
            case "guest":
                return <LoginWithGuest/>
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
    useContext(CLoginStatusRef).current.isLoggedIn = false;
    useEffect(() => {
        fetch(routeHelper.globalRoute("authLogout", { simulation_type: appName })).then(() => navigate(routeHelper.localRoute("root")));
    })


    return <>Signing out...</>
}
