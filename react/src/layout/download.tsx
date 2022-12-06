import usePortal from "react-useportal";
import React, { useContext, useRef } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import html2canvas from 'html2canvas';
import { downloadAs } from "../utility/download";
import { CPanelController } from "../data/panel";
import { LayoutProps, LayoutType } from "./layout";

export function LayoutWithDownloadButton<C, P>(Child: LayoutType<C, P>): LayoutType<C, P> {    
    return class extends Child {
        constructor(config: C) {
            super(config);

            let childComponent = this.component;
            this.component = (props: LayoutProps<P>) => {
                let ChildComponent = childComponent;
                let DownloadWrapper = this.downloadWrapper;
                return (
                    <DownloadWrapper {...props}>
                        <ChildComponent {...props}/>
                    </DownloadWrapper>
                )
            }
        }

        downloadWrapper = (props: LayoutProps<P> & { children: any }) => {
            let panelController = useContext(CPanelController);

            if(panelController) {
                let contentRef = useRef();
                let { Portal: ButtonPortal, portalRef } = usePortal({
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
