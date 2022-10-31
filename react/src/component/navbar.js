import { Navbar, Container } from "react-bootstrap";

export const NavbarContainerId = "nav-tabs-container";

export function SrNavbar(props) {
    let { title, titleHref } = props;
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
                {props.children}
            </Container>
        </Navbar>
    )
}
