import React, { useContext, useState } from "react"
import { Button, Col, Container, Form, Row } from "react-bootstrap"
import { Navigate, Route, Routes, useNavigate, useParams } from "react-router"
import { AppWrapper, AuthMethod, CAppName, CLoginStatus } from "../data/appwrapper"
import { useSetup } from "../hook/setup"

export const LoginRouter = (props) => {
    let appName = useContext(CAppName);
    const [hasLoginStatus, loginStatus] = useSetup(true, (new AppWrapper(appName)).getLoginStatus());
    return hasLoginStatus && (
        <CLoginStatus.Provider value={loginStatus}>
            <Routes>
                <Route path="login/*" element={<LoginRoot/>}/>
                <Route path="login-confirm/:method/:token/:needsCompleteRegistration" element={<LoginConfirm/>}/>
                <Route path="*" element={<CatchLoggedOut>{props.children}</CatchLoggedOut>}/>
            </Routes>
        </CLoginStatus.Provider>
    )
}

export const CatchLoggedOut = (props) => {
    let appName = useContext(CAppName);
    let loginStatus = useContext(CLoginStatus);
    return (
        <>
            {
                loginStatus.isLoggedIn ?
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
    needsCompleteRegistration: "0" | "1"
}

export const LoginConfirm = (props) => {
    let { token, method, needsCompleteRegistration } = useParams<LoginConfirmParams>();

    switch(method) {
        case 'email':
            return <LoginEmailConfirm needsCompleteRegistration={needsCompleteRegistration} token={token}/>
        default:
            throw new Error(`could not handle login method=${method}`)
    }
}

export const LoginEmailConfirm = (props) => {
    let { token, needsCompleteRegistration } = props;
    let appName = useContext(CAppName);
    let navigate = useNavigate();
    let completeLogin = (extra?: {[key: string]: any}) => {
        fetch(`/auth-email-authorized/${token}`, {
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
                needsCompleteRegistration ? (
                    <LoginEmailExtraInfoForm onComplete={(data) => completeLogin(data)}/>
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

export const LoginEmailExtraInfoForm = (props: { onComplete: ({fullName}) => void }) => {
    let { onComplete } = props;
    let [fullName, updateFullName] = useState<string>("");
    return (
        <>
            <p>Please enter your full name to complete your Sirepo registration.</p>
            <Form.Group as={Row} className="mb-3" controlId="formPlaintextEmail">
                <Form.Label column sm="3">
                    Your full name
                </Form.Label>
                <Col sm="9">
                    <Form.Control value={fullName} onChange={(e) => updateFullName(e.target.value)}/>
                </Col>
            </Form.Group>
            <Button variant="primary" onClick={() => onComplete({ fullName })}>Continue</Button>
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

    let doLogin = (email) => {
        appWrapper.doEmailLogin(email);
    }
    return (
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
    )
}
