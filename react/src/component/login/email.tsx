import React, { useContext, useState } from "react";
import { Button, Col, Container, Form, Modal, Row } from "react-bootstrap";
import { useNavigate } from "react-router";
import { CAppName, CAppWrapper, CLoginStatusRef } from "../../data/appwrapper";
import { CRouteHelper } from "../../utility/route";
import { LoginExtraInfoForm, updateLoginStatusRef } from "./login";

export const LoginEmailConfirm = (props) => {
    let { token, needCompleteRegistration } = props;
    let appName = useContext(CAppName);
    let routeHelper = useContext(CRouteHelper);
    let loginStatusRef = useContext(CLoginStatusRef);
    let appWrapper = useContext(CAppWrapper);
    let navigate = useNavigate();
    let completeLogin = (extra?: {[key: string]: any}) => {
        fetch(routeHelper.globalRoute("authEmailAuthorized", {
            simulation_type: appName,
            token: token
        }), {
            method: "POST",
            body: JSON.stringify({ token, ...(extra || {}) }),
            headers: {
                "Content-Type": "application/json"
            }
        }).then(() =>
        updateLoginStatusRef(loginStatusRef, appWrapper)
        .then(() => navigate(`/${appName}`))
        )
    }

    return (
        <Container>
            {
                needCompleteRegistration === '1' ? (
                    <LoginExtraInfoForm onComplete={(data) => completeLogin(data)}/>
                ) : (
                    <>
                        <p>Please click the button below complete the login process.</p>
                        <Button onClick={() => completeLogin()}>Confirm</Button>
                    </>
                )
            }
        </Container>
    )
}

export const LoginWithEmail = (props) => {
    let [email, updateEmail] = useState<string>("");
    let appWrapper = useContext(CAppWrapper);

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
                        <Button variant="primary" onClick={() => doLogin(email)} disabled={! (email && email.match(/^.+@.+\..+$/))}>Continue</Button>
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
