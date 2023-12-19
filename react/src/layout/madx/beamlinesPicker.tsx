import React, { useState } from "react"
import { FunctionComponent, useContext } from "react"
import { Button, Table } from "react-bootstrap"
import { useDispatch, useStore } from "react-redux"
import { HoverController } from "../../component/reusable/hover"
import { StoreTypes } from "../../data/data"
import { Dependency } from "../../data/dependency"
import { CHandleFactory } from "../../data/handle"
import { ArrayFieldState } from "../../store/common"
import { ModelState } from "../../store/models"
import { Layout } from "../layout"
import "./beamlines.scss";

export type MadxBeamlinesPickerConfig = {
    selectedBeamlineDependency: string
    beamlinesDependency: string
}

export class MadxBeamlinesPickerLayout extends Layout<MadxBeamlinesPickerConfig> {
    component: FunctionComponent<{ [key: string]: any }> = (props) => {
        let handleFactory = useContext(CHandleFactory);
        let store = useStore();
        let dispatch = useDispatch();
        let selectedBeamlineIdHandle = handleFactory.createHandle(new Dependency(this.config.selectedBeamlineDependency), StoreTypes.Models).hook();
        let selectedBeamline: number = selectedBeamlineIdHandle.value as number;
        let beamlinesHandle = handleFactory.createHandle(new Dependency(this.config.beamlinesDependency), StoreTypes.Models).hook();
        let beamlines: ArrayFieldState<ModelState> = beamlinesHandle.value as ArrayFieldState<ModelState>;

        let selectBeamline = (id: number) => {
            if(id !== selectedBeamline) {
                selectedBeamlineIdHandle.write(id, store.getState(), dispatch);
            }
        }

        return (
            <Table className="w-100">
                <thead>
                    <tr>
                        <th>
                            Name
                        </th>
                        {/*<th>
                            Description
                         </th>*/}
                        <th>
                            Length
                        </th>
                        <th>
                            Bend
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <HoverController>
                    {
                        (hover) => {
                            return beamlines.map(bl => bl.item).map(bl => {
                                let name = bl.name as string;
                                let id = bl.id as number;
                                let isSelected = selectedBeamline === id;
                                return (
                                    <>
                                        <tr key={id} onMouseEnter={() => hover.aquireHover(id)} onMouseLeave={() => hover.releaseHover(id)} style={
                                            {
                                                backgroundColor: isSelected ? "#dff0d8" : undefined,
                                                /*filter: isHovered ? "brightness(75%)" : undefined*/
                                            }
                                        }>
                                            <td>
                                                {`${name}`}
                                            </td>
                                            {/*<td>
                                                TODO: description
                                            </td>*/}
                                            <td>
                                                {(bl.length as number).toPrecision(4)}
                                            </td>
                                            <td>
                                                {(bl.angle as number).toPrecision(4)}
                                            </td>
                                        </tr>
                                        {
                                            hover.checkHover(id) && (
                                                <tr className="popover-buttons-outer" onMouseEnter={() => hover.aquireHover(id)} onMouseLeave={() => hover.releaseHover(id)}>
                                                    <td className="popover-buttons" style={{ bottom: "-2px" }}>
                                                        <Button className="popover-button" size="sm" variant="primary" onClick={() => selectBeamline(id)}>
                                                            Select
                                                        </Button>
                                                    </td>
                                                </tr>
                                            )
                                        }
                                    </>
                                )
                            })
                        }
                    }
                    </HoverController>
                </tbody>
            </Table>
        )
    }
}
