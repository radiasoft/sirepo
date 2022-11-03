import React from "react";
import { Table } from "../component/reusable/table";
import { View }from "./layout";

function apiResponseToTableConfig(apiResponse, attributeName) {
    let data = apiResponse[attributeName || 'data'];

    if(!data) {
        return undefined;
    }

    let rowNames = [];
    let columnNames = [];
    let rows = [];

    for(let [rowName, row] of data) {
        rowNames.push(rowName);
        rows.push(row);
    }

    return {
        rowNames,
        rows,
        columnNames
    }
}

export class TableFromApi extends View {
    getFormDependencies = (config) => {
        return [];
    }

    component = (props) => {
        let { simulationData, config } = props;

        let { dataAttributeName } = config;

        let tableConfig = apiResponseToTableConfig(simulationData, dataAttributeName);

        return (
            <>{tableConfig && <Table {...tableConfig} {...props}/>}</>
        )
    }
}
