import { Navbar, Container, Nav, Col, NavDropdown, Row } from "react-bootstrap";
import React, { ReactNode, useRef } from "react";
import "./navbar.scss";
import { v4 as uuidv4 } from 'uuid';
import { NavbarAuthStatus } from "../login/login";

export const NavbarContainerId = "nav-tabs-container";

export function SrNavbar(props) {
    let { title, titleHref, simulationsHref } = props;
    return (
        <Navbar className="sr-navbar" bg="light">
            <div className="sr-navbar-container" id={NavbarContainerId}>
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
                <div>
                    <Nav>
                        <Nav.Link href={simulationsHref}><span className="sr-navbar-simulations-button">Simulations</span></Nav.Link>
                    </Nav>
                </div>
                <div className="sr-navbar-spacer">
                </div>
                <div className="flex-grow-1 order-3"></div>
                {props.children}
            </div>
        </Navbar>
    )
}

export const NavToggleDropdown = (props: {title: ReactNode, children?: ReactNode[]}) => {
    let { title } = props;

    let id = useRef<string>(uuidv4());

    return (
        <>
            <Navbar.Toggle aria-controls={id.current} />
            <Navbar.Collapse id={id.current}>
                <Nav>
                    <NavDropdown
                        title={title}
                    >
                        {props.children}
                    </NavDropdown>
                </Nav>
            </Navbar.Collapse>
        </>
    )
}
