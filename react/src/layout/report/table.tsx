import React from "react";
import { Table, TableConfig } from "../../component/reusable/table";
import { LayoutProps }from "../layout";
import { ReportVisual, ReportVisualProps } from "../report";

export type TableConfigApi = [
    [string, number[]]
]

function apiResponseToTableConfig(apiResponse: any, attributeName: string): TableConfig {
    if(!apiResponse) return undefined;

    let data = apiResponse[attributeName || 'data'] as TableConfigApi;

    if(!data) {
        return undefined;
    }

    let rowNames = [];
    let columnNames = apiResponse.headings ? apiResponse.headings.slice() : [];
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

export class TableFromApi extends ReportVisual<TableFromApiConfig, {}, TableConfigApi, TableConfig> {
    getConfigFromApiResponse(apiReponse: TableConfigApi): TableConfig {
        return apiResponseToTableConfig(apiReponse, this.config.dataAttributeName);
    }

    canShow(apiResponse: TableConfigApi): boolean {
        return !!this.getConfigFromApiResponse(apiResponse);
    }

    component = (props: LayoutProps<{}> & ReportVisualProps<TableConfig>) => {
        let { data } = props;

        return (
            <Table {...data} {...props}/>
        )
    }
}
