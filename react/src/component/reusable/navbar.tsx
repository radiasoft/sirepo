import { Navbar, Container, Nav, Col, NavDropdown, Row } from "react-bootstrap";
import React, { ReactNode, useRef } from "react";
import "./navbar.scss";
import { v4 as uuidv4 } from 'uuid';

export const NavbarRightContainerId = "nav-tabs-right-container";
export const NavbarLeftContainerId = "nav-tabs-left-container";

export function SrNavbar(props) {
    let { title, titleHref, simulationsHref } = props;
    return (
        <Navbar className="sr-navbar" bg="light">
            <div className="sr-navbar-container">
                <div className="sr-navbar-container justify-content-start order-1" id={NavbarLeftContainerId}>
                    <Navbar.Brand href={titleHref} className="order-1">
                        <img
                        alt=""
                        src="/react/img/sirepo.gif"
                        width="30"
                        height="30"
                        className="d-inline-block align-top"
                        />{' '}
                        {title}
                    </Navbar.Brand>
                    <Nav className="order-1">
                        <Nav.Link href={simulationsHref}><span className="sr-navbar-simulations-button">Simulations</span></Nav.Link>
                    </Nav>
                    <div className="sr-navbar-spacer order-1"/>
                </div>
                <div className="flex-grow-1 order-3"></div>
                <div className="sr-navbar-container justify-content-end order-4" id={NavbarRightContainerId}>
                    {props.children}
                </div>
            </div>
        </Navbar>
    )
}

export const NavToggleDropdown = (props: {title: ReactNode, children?: ReactNode[] | ReactNode}) => {
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
