import React, { useContext, useState } from "react"
import { Button, Col, Container, Form, Row } from "react-bootstrap"
import { Route, Routes } from "react-router"
import { AppWrapper, CAppName, CLoginStatus } from "../data/appwrapper"

export const LoginRouter = (props) => {
    return (
        <Routes>
            <Route path="login/*" element={<LoginRoot/>}/>
            <Route path="*" element={props.children}/>
        </Routes>
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
