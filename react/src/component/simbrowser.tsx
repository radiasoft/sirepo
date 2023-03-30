import { trimPathSeparators, joinPath } from "../utility/path";
import React, { useContext } from "react";
import {
    Accordion,
    Container,
    Row,
    Col
} from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import * as IconRegular from "@fortawesome/free-regular-svg-icons";
import { Link, Route, Routes, Navigate, useParams } from "react-router-dom";
import { SimulationRoot } from "./simulation";
import { CRouteHelper } from "../utility/route";
import "./simbrowser.scss";
import { NavbarLeftContainerId } from "./reusable/navbar";
import { CSimulationList, SimulationListItem } from "../data/appwrapper";
import { Portal } from "./reusable/portal";

export type SimulationTreeNode = {
    name: string,
    folder: string,
    folders: SimulationTreeNode[],
    items: SimulationListItem[]
}

function buildSimulationsTree(simulations: SimulationListItem[]): SimulationTreeNode {
    let root: SimulationTreeNode = {
        name: '/',
        folder: '',
        folders: [],
        items: []
    }

    let createFolderIfNotExists = (tree: SimulationTreeNode, folderName: string, fullFolderPath: string): SimulationTreeNode => {
        if(tree.folders === undefined) {
            tree.folders = [];
        }
        let findChild = () => tree.folders.find(c => c.name === folderName) as SimulationTreeNode;
        if(!findChild()) {
            tree.folders.push({ name: folderName, folder: fullFolderPath, folders: [], items: [] });
        }
        return findChild();
    }

    let placeItemIntoFolder = (simulation: SimulationListItem): void => {
        simulation.folder = trimPathSeparators(simulation.folder, { front: true, end: true });
        let paths = simulation.folder.split('/');

        let tree = root;

        let fullPath = '';
        for(let segment of paths) {
            if(!segment || segment.length === 0) continue; // handle leading and double? /
            fullPath = joinPath(fullPath, segment);
            tree = createFolderIfNotExists(tree, segment, fullPath);
        }

        tree.items = tree.items || [];
        tree.items.push(simulation);
    }

    for(let item of simulations) {
        placeItemIntoFolder(item);
    }

    return root;
}

function SimulationTreeViewFolder(props: {
    tree: SimulationTreeNode,
    isRoot: boolean,
    path: string[]
}) {
    let { tree, isRoot, path } = props;

    let routeHelper = useContext(CRouteHelper);

    let childElements = [];
    for(let item of tree.items) {
        childElements.push(<SimulationTreeViewItem key={joinPath(item.folder, item.name)} item={item}/>);
    }

    for(let folder of tree.folders) {
        let [, ...restPath] = path;
        childElements.push(<SimulationTreeViewFolder key={joinPath(folder.folder, folder.name)} isRoot={false} tree={folder} path={restPath}/>);
    }

    //let subpath = routeHelper.getRelativePath(joinPath('/simulations', encodeURI(tree.folder)));
    let subpath = joinPath(routeHelper.localRoute("simulations"), encodeURI(tree.folder));
    let shouldBeOpen = isRoot || (path.length > 0 && path[0] === tree.name);

    return <Accordion defaultActiveKey={shouldBeOpen ? '0' : undefined}>
        <Accordion.Item eventKey="0">
            <Accordion.Header>
                <Link to={subpath} key={subpath}>{tree.name}</Link>
            </Accordion.Header>
            <Accordion.Body>
                {childElements}
            </Accordion.Body>
        </Accordion.Item>
    </Accordion>
}

function SimulationTreeViewItem(props: {
    item: SimulationListItem
}) {
    let { item } = props;
    let routeHelper = useContext(CRouteHelper);

    //let path = routeHelper.getRelativePath(joinPath('source', item.simulationId));
    let path = routeHelper.localRoute("source", {
        simulationId: item.simulationId
    })

    return (
        <div className="sr-sim-tree-view-item">
            <Link to={path} key={path}>{item.name}</Link>
        </div>
    )
}

function SimulationIconView(props: {
    tree: SimulationTreeNode
}) {
    let { tree } = props;

    let elements = [
        ...tree.folders.map(c => <SimulationIconViewFolder key={joinPath(c.folder, c.name)} tree={c}/>),
        ...tree.items.map(c => <SimulationIconViewItem key={joinPath(c.folder, c.name)} item={c}/>)
    ]

    return (
        <div className="sr-sim-icon-view mt-3">
            {elements}
        </div>
    )
}

function SimulationIconViewFolder(props: {
    tree: SimulationTreeNode
}) {
    let { tree } = props;

    return (
        <Link to={joinPath('./', tree.name)}>
            <div className="sr-sim-icon-view-base sr-sim-icon-view-folder">
                <div className="sr-sim-icon-view-icon-outer">
                    <FontAwesomeIcon className="sr-sim-icon-view-icon sr-sim-icon-view-folder-icon" icon={Icon.faFolder}/>
                </div>
                <div className="sr-sim-icon-view-name text-center">
                    <span>
                        {tree.name}
                    </span>
                </div>
            </div>
        </Link>
    )
}

function SimulationIconViewItem(props: {
    item: SimulationListItem
}) {
    let { item } = props;

    let routeHelper = useContext(CRouteHelper);

    //let path = routeHelper.getRelativePath(item.simulationId)
    let path = routeHelper.localRoute("source", {
        simulationId: item.simulationId
    })

    return (
        <Link to={path}>
            <div className="sr-sim-icon-view-base sr-sim-icon-view-folder">
                <div className="sr-sim-icon-view-icon-outer">
                    <FontAwesomeIcon className="sr-sim-icon-view-icon sr-sim-icon-view-folder-icon" icon={IconRegular.faFile} />
                </div>
                <div className="sr-sim-icon-view-name text-center">
                    <span>
                        {item.name}
                    </span>
                </div>
            </div>
        </Link>
    )
}

function SimulationFolderRouter(props: { tree: SimulationTreeNode, path: string[], children: ({routedTree, routedPath}: {routedTree: SimulationTreeNode, routedPath: string[]}) => React.ReactElement }) {
    let { tree, path } = props;
    path = path || [];
    let { simulationFolder } = useParams();

    let childFn = props.children || (() => undefined);

    if(simulationFolder) {
        path.push(simulationFolder);
        let matchedFolder = tree.folders.find(c => c.name === simulationFolder);

        if(!matchedFolder) {
            return <>Folder {simulationFolder} not found!</> //TODO 404
        } else {
            tree = matchedFolder;
        }
    }

    let el = childFn({routedTree: tree, routedPath: path})
    // TODO: this calls childFn even if route is not a match
    return (
        <Routes>
            <Route path="/" element={
                <>{el}</>
            }/>
            <Route path="/:simulationFolder/*" element={
                <SimulationFolderRouter tree={tree} path={[]}>{props.children}</SimulationFolderRouter>
            }/>
        </Routes>
    )
}

function SimulationRouteHeader(props: {
    path: string[]
}) {
    let { path } = props;
    let routeHelper = useContext(CRouteHelper);

    let prevSegments = [];
    let elements = (path || []).map(pathSegment => {
        //let routePath = routeHelper.getRelativePath(joinPath('/simulations', ...prevSegments, pathSegment));
        let routePath = joinPath(routeHelper.localRoute("simulations"), ...prevSegments, pathSegment);
        prevSegments.push(pathSegment);
        return (
            <React.Fragment key={routePath}>
                <span className="sr-sim-route-header-separator sr-sim-route-header-text">/</span>
                <Link to={routePath}>
                    <span className="sr-sim-route-header-segment sr-sim-route-header-text">
                        {pathSegment}
                    </span>
                </Link>
            </React.Fragment>
        )
    })

    return (
        <div className="sr-sim-route-header">
            {elements}
        </div>
    )
}

function SimulationBrowser(props: {
    tree: SimulationTreeNode
}) {
    let { tree } = props;

    return (
        <SimulationFolderRouter path={[]} tree={tree}>
            {({routedTree, routedPath}) => {
                return (
                    <>
                        <Portal targetId={NavbarLeftContainerId} className="order-4">
                            <SimulationRouteHeader path={routedPath}/>
                        </Portal>
                        <div className="sr-sim-browser-outer">
                            <Container fluid className="sr-sim-browser">
                                <Row sm={2}>
                                    <Col sm={4}>
                                        <SimulationTreeViewFolder isRoot={true} tree={tree} path={routedPath}/>
                                    </Col>
                                    <Col sm={8}>
                                        <SimulationIconView tree={routedTree}/>
                                    </Col>
                                </Row>
                            </Container>
                        </div>
                    </>

                )
            }}
        </SimulationFolderRouter>
    )
}

function SimulationRootWrapper(props) {
    let { simulationId } = useParams();
    return <SimulationRoot key={simulationId} simulationId={simulationId}/> // TODO: error/missing handling
}

export function SimulationBrowserRoot(props) {
    let simulationList = useContext(CSimulationList);
    let simulationTree = buildSimulationsTree(simulationList);
    let routeHelper = useContext(CRouteHelper);

    let child = (
        <Routes>
            <Route path="/" element={
                <Navigate to={routeHelper.localRoute("simulations")}></Navigate>
            }/>
            <Route path={`${routeHelper.localRoutePattern("simulations")}/*`} element={<SimulationBrowser tree={simulationTree} />}/>
            <Route path={`${routeHelper.localRoutePattern("source")}/*`} element={
                <SimulationRootWrapper simulationList={simulationList}/>
            }/>
        </Routes>
    )

    return (
        <>
            {child}
        </>
    );
}
