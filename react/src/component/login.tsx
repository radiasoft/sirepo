import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import React, { useContext, useEffect, useState } from "react"
import { Button, Col, Container, Dropdown, Form, Image, Modal, Nav, Row } from "react-bootstrap"
import { Navigate, Route, Routes, useNavigate, useParams } from "react-router"
import { AppWrapper, AuthMethod, CAppName, CLoginStatus, CSchema } from "../data/appwrapper"
import { useSetup } from "../hook/setup"
import { NavbarContainerId, NavToggleDropdown } from "./reusable/navbar";
import { Portal } from "./reusable/portal";
import "./login.scss";

export const LoginRouter = (props) => {
    let appName = useContext(CAppName);
    const [hasLoginStatus, loginStatus] = useSetup(true, (new AppWrapper(appName)).getLoginStatus());

    return hasLoginStatus && (
        <CLoginStatus.Provider value={loginStatus}>
            <Portal targetId={NavbarContainerId} className="order-5 sr-navbar-auth">
                <NavbarAuthStatus/>
            </Portal>
            <Routes>
                <Route path="logout/*" element={<LogoutRoot/>}/>
                <Route path="login/*" element={<LoginRoot/>}/>
                <Route path="login-confirm/:method/:token/:needCompleteRegistration" element={<LoginConfirm/>}/>
                <Route path="*" element={<CatchLoggedOut>{props.children}</CatchLoggedOut>}/>
            </Routes>
        </CLoginStatus.Provider>
    )
}

export const NavbarAuthStatus = (props) => {
    let loginStatus = useContext(CLoginStatus);
    let schema = useContext(CSchema);
    let appName = useContext(CAppName);
    let appWrapper = new AppWrapper(appName);

    if(loginStatus.isLoggedIn) {
        return (
            <NavToggleDropdown title={
                <>{
                    loginStatus.avatarUrl ? (
                        <Image src={loginStatus.avatarUrl} fluid rounded={true}/>
                    ) : (
                        <FontAwesomeIcon icon={Icon.faUser}/>
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
                <Dropdown.Header>{loginStatus.userName}</Dropdown.Header>
                <Dropdown.Item href={`/${appName}/logout`}>Sign Out</Dropdown.Item>
            </NavToggleDropdown>
        )
    }

    return (
        <Nav.Link href={`/${appName}/login`}>Sign In</Nav.Link>
    )


}

export const CatchLoggedOut = (props) => {
    let appName = useContext(CAppName);
    let loginStatus = useContext(CLoginStatus);

    return (
        <>
            {
                loginStatus.isLoggedIn && !loginStatus.needCompleteRegistration ?
                (
                    props.children
                ) : (
                    <Navigate to={`/react/${appName}/login`}/> // TODO @garsuga: abstract
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

export const LoginEmailConfirm = (props) => {
    let { token, needCompleteRegistration } = props;
    let appName = useContext(CAppName);
    let navigate = useNavigate();
    let completeLogin = (extra?: {[key: string]: any}) => {
        fetch(`/auth-email-authorized/${appName}/${token}`, {
            method: "POST",
            body: JSON.stringify({ token, ...(extra || {}) }),
            headers: {
                "Content-Type": "application/json"
            }
        }).then(() => navigate(`/react/${appName}`))
    }
    return (
        <Container>
            {
                needCompleteRegistration ? (
                    <LoginExtraInfoForm onComplete={(data) => completeLogin(data)}/>
                ) : (
                    <>
                        <p>Click the button complete the login process.</p>
                        <Button onClick={() => completeLogin()}>Continue</Button>
                    </>
                )
            }
        </Container>
    )
}

export const LoginNeedCompleteRegistration = (props) => {
    let appName = useContext(CAppName);
    let navigate = useNavigate();
    let onCompleteForm = (data: {[key: string]: any}) => {
        fetch(`/auth-complete-registration`, {
            method: "POST",
            body: JSON.stringify({ ...data, simulationType: appName }),
            headers: {
                "Content-Type": "application/json"
            }
        }).then(() => navigate(`/react/${appName}`))
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
    let getLoginComponent = (method: string): JSX.Element => {
        switch(method) {
            case "email":
                return <LoginWithEmail/>

            default:
                throw new Error(`could not handle login method=${method}`)
        }
    }

    let loginStatus = useContext(CLoginStatus);
    let appName = useContext(CAppName);

    if(loginStatus.needCompleteRegistration) {
        return (
            <Container className="sm-12 lg-6">
                <LoginNeedCompleteRegistration/>
            </Container>
            
        )
    }

    if(loginStatus.isLoggedIn && !loginStatus.needCompleteRegistration) {
        return (
            <Navigate to={new AppWrapper(appName).getAppRootLink()}></Navigate>
        )
    }

    return (
        <Container className="sm-12 lg-6">
            {getLoginComponent(loginStatus.visibleMethod)}
        </Container>
    )
}

export const LoginWithEmail = (props) => {
    let [email, updateEmail] = useState<string>("");
    let appName = useContext(CAppName);
    let appWrapper = new AppWrapper(appName);

    let [emailSent, updateEmailSent] = useState<boolean>(false);

    let doLogin = (email) => {
        appWrapper.doEmailLogin(email);
        updateEmailSent(true);
    }
    return (
        <>
            <LoginEmailSent email={email} show={emailSent}/>
            <Container>
                <Row>
                    <p className="text-secondary">
                        Enter your email address and we'll send an authorization link to your inbox.
                    </p>
                </Row>
                <Form.Group as={Row} className="mb-3" controlId="formPlaintextEmail">
                    <Form.Label column sm="2">
                        Email
                    </Form.Label>
                    <Col sm="8">
                        <Form.Control placeholder="email@example.com" value={email} onChange={(e) => updateEmail(e.target.value)}/>
                    </Col>
                    <Col sm="2">
                        <Button variant="primary" onClick={() => doLogin(email)}>Continue</Button>
                    </Col>
                </Form.Group>
                <Row>
                    <p className="text-secondary">
                        By signing up for Sirepo you agree to Sirepo's privacy policy and terms and conditions, and to receive informational and marketing communications from RadiaSoft. You may unsubscribe at any time.
                    </p>
                </Row>
            </Container>
        </>
    )
}

export function LoginEmailSent(props: { email: string, show: boolean }) {
    let { email, show } = props;

    return (
        <Modal show={show}>
            <Modal.Header>
                <Modal.Title>Check your inbox</Modal.Title>
            </Modal.Header>

            <Modal.Body>
                <p>We just emailed a confirmation link to {email}. Click the link and you'll be signed in. You may close this window.</p>
            </Modal.Body>
        </Modal>
    )
}

export function LogoutRoot(props) {
    let navigate = useNavigate();
    let appName = useContext(CAppName);

    useEffect(() => {
        fetch(`/auth-logout/${appName}`).then(() => navigate(new AppWrapper(appName).getAppRootLink()));
    })
    

    return <>Singing out...</>
}
