import { Navbar, Nav, NavDropdown } from "react-bootstrap";
import React, { ReactNode, useRef } from "react";
import "./navbar.scss";
import { v4 as uuidv4 } from 'uuid';
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { AlignType } from "react-bootstrap/esm/types";
import { DropDirection } from "react-bootstrap/esm/DropdownContext";

export const NavbarRightContainerId = "nav-tabs-right-container";
export const NavbarLeftContainerId = "nav-tabs-left-container";
export const NavbarHelpMenuContainerId = "nav-help-container";

// TODO: this is no longer reusable
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
                <div className="flex-grow-1 order-3"/>
                <div className="sr-navbar-container justify-content-end order-4" id={NavbarRightContainerId}>
                    <NavToggleDropdown align="end" drop="down" className="order-4 col-auto flex-grow-0" title={
                        <FontAwesomeIcon icon={Icon.faQuestionCircle}/>
                    }>
                        <NavDropdown.Item href="https://github.com/radiasoft/sirepo/issues">Report a Bug</NavDropdown.Item>
                        <div id={NavbarHelpMenuContainerId}/>
                    </NavToggleDropdown>
                    {props.children}
                </div>
            </div>
        </Navbar>
    )
}

export const NavToggleDropdown = (props: {title: ReactNode, children?: ReactNode[] | ReactNode, align?: AlignType, drop?: DropDirection } & {[key: string]: any}) => {
    let { title, align, drop, ...otherProps } = props;

    let id = useRef<string>(uuidv4());

    return (
        <>
            <Navbar.Toggle aria-controls={id.current} />
            <Navbar.Collapse id={id.current} {...otherProps}>
                <Nav>
                    <NavDropdown
                        drop={drop}
                        align={align}
                        title={title}
                    >
                        {props.children}
                    </NavDropdown>
                </Nav>
            </Navbar.Collapse>
        </>
    )
}
