import { Navbar, Container, Nav } from "react-bootstrap";
import React from "react";
import "./navbar.scss";

export const NavbarContainerId = "nav-tabs-container";

export function SrNavbar(props) {
    let { title, titleHref, simulationsHref } = props;
    return (
        <Navbar>
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
                <Nav>
                    <Nav.Link href={simulationsHref}><span className="sr-navbar-simulations-button">Simulations</span></Nav.Link>
                </Nav>
                <div className="sr-navbar-spacer">
                </div>
                {props.children}
            </Container>
        </Navbar>
    )
}
