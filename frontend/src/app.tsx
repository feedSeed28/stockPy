import DataSourceSwitch from "@/components/DataSourceSwitch";

export const request = {
  timeout: 10000,
};

export function layout() {
  return {
    rightRender: () => <DataSourceSwitch />,
    actionsRender: () => [<DataSourceSwitch key="ds" />],
  };
}
