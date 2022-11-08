import { Button } from "react-bootstrap";
import usePortal from "react-useportal";
import React, { useContext, useRef } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import html2canvas from 'html2canvas';
import { downloadAs } from "../utility/download";
import { CPanelController } from "../data/panel";
import { LayoutProps, LayoutType, View } from "./layout";
import { LayoutWrapper } from "./layouts";

export function LayoutWithDownloadButton<P>(Child: LayoutType<P>): LayoutType<P> {
    return class extends View<P> {
        child: View<P>;

        constructor(layoutWrapper: LayoutWrapper) {
            super(layoutWrapper);
            this.child = new Child(layoutWrapper);
        }

        getFormDependencies(config: P) {
            return this.child.getFormDependencies(config);
        }

        component = (props: LayoutProps<P>) => {
            let ChildComponent = this.child.component;
            let DownloadWrapper = this.downloadWrapper;
            return (
                <DownloadWrapper {...props}>
                    <ChildComponent {...props}/>
                </DownloadWrapper>
            )
        }

        downloadWrapper = (props) => {
            let portalFn = usePortal;
            let contextFn = useContext;
            let refFn = useRef;

            let panelController = contextFn(CPanelController);

            if(panelController) {
                let contentRef = refFn();
                let { Portal: ButtonPortal, portalRef } = portalFn({
                    bindTo: document && document.getElementById(panelController.buttonPortalId)
                })

                if(portalRef && portalRef.current) {
                    portalRef.current.classList.add("d-inline");
                }

                let download = () => {
                    let contentElement = contentRef.current;
                    html2canvas(contentElement).then((canvas) => {
                        canvas.toBlob(function(blob) {
                            downloadAs(blob, "report.png");
                        });
                    })
                }

                return (
                    <>
                        <ButtonPortal>
                            <a className="ms-2" onClick={download}>
                                <FontAwesomeIcon fixedWidth icon={Icon.faDownload}/>
                            </a>
                        </ButtonPortal>
                        <div ref={contentRef}>
                            {props.children}
                        </div>
                    </>
                )
            }

            return <>{props.children}</>
        }
    };
}
