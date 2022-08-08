import { Col, Row, Container } from "react-bootstrap";
import { mapProperties } from "../helper";

export function ViewGrid(props) {
    let { views, ...otherProps } = props;
    let viewPanels = Object.entries(views).map(([id, view]) => {
        let View = view;
        return (
            <Col md={6} className="mb-3" key={id}>
                <View {...otherProps}/>
            </Col>
        )
    });
    return (
        <Container fluid className="mt-3">
            <Row>
                {viewPanels}
            </Row>
        </Container>
    )
}
