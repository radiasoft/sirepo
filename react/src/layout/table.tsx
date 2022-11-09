import React from "react";
import { Table } from "../component/reusable/table";
import { LayoutProps, View }from "./layout";

export type TableConfigApi = [
    [string, number[]]
]

function apiResponseToTableConfig(apiResponse: any, attributeName: string) {
    let data = apiResponse[attributeName || 'data'] as TableConfigApi;

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

export type TableFromApiConfig = {
    dataAttributeName: string
}

export type TableFromApiExtraProps = {
    simulationData: any
}

export class TableFromApi extends View<TableFromApiConfig, TableFromApiExtraProps> {
    getFormDependencies = (config: TableFromApiConfig) => {
        return [];
    }

    component = (props: LayoutProps<TableFromApiConfig, TableFromApiExtraProps>) => {
        let { simulationData, config } = props;

        let { dataAttributeName } = config;

        let tableConfig = apiResponseToTableConfig(simulationData, dataAttributeName);

        return (
            <>{tableConfig && <Table {...tableConfig} {...props}/>}</>
        )
    }
}
