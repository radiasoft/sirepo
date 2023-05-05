import { FunctionComponent, useContext, useState } from "react";
import { getValueSelector, revertDataStructure, StoreTypes } from "../../data/data";
import { FormStateHandleFactory } from "../../data/form";
import { CHandleFactory } from "../../data/handle";
import { Layout } from "../layout";
import { TemplateSettings } from "./allBeamlineElements";
import { Dependency } from "../../data/dependency";
import { ArrayFieldElement, ArrayFieldState } from "../../store/common";
import { ModelState } from "../../store/models";
import React from "react";
import { Badge } from "react-bootstrap";
import { useCoupledState } from "../../hook/coupling";
import { useDispatch, useStore } from "react-redux";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import * as IconRegular from "@fortawesome/free-regular-svg-icons";

export type MadxBeamlineElmenetsConfig = {
    selectedBeamlineDependency: string,
    beamlinesDependency: string,
    elementsDependency: string,
    elementTemplates: TemplateSettings[]
}

export class MadxBeamlineElementsLayout extends Layout<MadxBeamlineElmenetsConfig> {
    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let handleFactory = useContext(CHandleFactory) as FormStateHandleFactory;
        let store = useStore();
        let dispatch = useDispatch();
        let isDirty = handleFactory.isDirty();

        let selectedBeamlineHandle = handleFactory.createHandle(new Dependency(this.config.selectedBeamlineDependency), StoreTypes.Models).hook();
        // handles case where selected beamline changes and form is dirty
        let _ = useCoupledState(selectedBeamlineHandle.value, () => {
            if(isDirty) {
                handleFactory.cancel(store.getState(), dispatch);
            }
            return selectedBeamlineHandle.value;
        })
        let beamlinesHandle = handleFactory.createHandle(new Dependency(this.config.beamlinesDependency), StoreTypes.FormState).hook();
        let beamlinesValue = revertDataStructure(beamlinesHandle.value, getValueSelector(StoreTypes.FormState)) as ArrayFieldState<ModelState>;
        let elementsHandle = handleFactory.createHandle(new Dependency(this.config.elementsDependency), StoreTypes.FormState).hook();
        let elementsValue = revertDataStructure(elementsHandle.value, getValueSelector(StoreTypes.FormState)) as ArrayFieldState<ModelState>;

        let _allItems = [...elementsValue, ...beamlinesValue];
        let findBeamlineOrElementById = (id: number): ArrayFieldElement<ModelState> => {
            return _allItems.find(i => i.item.id === id || i.item._id === id);
        }
        console.log("selectedBeamline", selectedBeamlineHandle.value);
        console.log("elementsValue", elementsValue);

        let currentBeamline = beamlinesValue.find(beam => beam.item.id === selectedBeamlineHandle.value).item;
        console.log("currentBeamline", currentBeamline);
        let beamlineElements = (currentBeamline.items as number[]).map(findBeamlineOrElementById)
        console.log("beamlineElements", beamlineElements);

        let [hoveredElement, updateHoveredElement] = useState<number>(undefined);

        return (
            <div className="d-flex flex-row" style={{ flexWrap: "wrap" }}>
                {
                    beamlineElements.map(e => {
                        let id = (e.item._id !== undefined ? e.item._id : e.item.id) as number;
                        let isHovered = id === hoveredElement;
                        return (
                            <div key={id} className="d-flex flex-row flex-nowrap" onMouseEnter={() => updateHoveredElement(id)} onMouseLeave={() => isHovered && updateHoveredElement(undefined)}>
                                <Badge bg="primary">
                                    {`${e.item.name as string}`}
                                </Badge>
                                <div style={{width: "25px", height: "25px"}}>
                                    <div style={{ display: isHovered ? "block" : "none" }}>
                                        <FontAwesomeIcon icon={Icon.faClose} onClick={() => null}/>
                                    </div>
                                </div>
                            </div>
                        )
                    })
                }
            </div>
        )
    }
}
