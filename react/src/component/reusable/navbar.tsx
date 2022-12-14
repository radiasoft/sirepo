import { Navbar, Container, Nav, Col } from "react-bootstrap";
import React from "react";
import "./navbar.scss";

export const NavbarContainerId = "nav-tabs-container";

export function SrNavbar(props) {
    let { title, titleHref, simulationsHref } = props;
    return (
        <Navbar bg="light">
            <Container fluid id={NavbarContainerId}>
                <Navbar.Brand href={titleHref}>
                    <img
                    alt=""
                    src="/react/img/sirepo.gif"
                    width="30"
                    height="30"
                    className="d-inline-block align-top"
                    />{' '}
                    {title}
                </Navbar.Brand>
                <Col className="float-left">
                    <Nav>
                        <Nav.Link href={simulationsHref}><span className="sr-navbar-simulations-button">Simulations</span></Nav.Link>
                    </Nav>
                </Col>
                <div className="sr-navbar-spacer">
                </div>
                {props.children}
            </Container>
        </Navbar>
    )
}
