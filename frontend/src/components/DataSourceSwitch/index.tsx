/** 右上角数据源切换开关 */
import { Switch, Space, Tag, message, Tooltip } from "antd";
import { ThunderboltOutlined, DatabaseOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import {
  getDataSourceMode,
  setDataSourceMode,
  type DataSourceMode,
} from "@/utils/dataSource";

export default function DataSourceSwitch() {
  const [mode, setMode] = useState<DataSourceMode>(getDataSourceMode);

  useEffect(() => {
    const onStorage = () => setMode(getDataSourceMode());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const isDirect = mode === "direct";

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        height: "100%",
        gap: 8,
        paddingRight: 16,
      }}
    >
      <Tooltip title={isDirect ? "浏览器直连东方财富" : "后端 FastAPI → MySQL"}>
        <Tag
          color={isDirect ? "orange" : "blue"}
          style={{ cursor: "default", margin: 0, lineHeight: "22px" }}
        >
          {isDirect ? (
            <><ThunderboltOutlined /> 直连</>
          ) : (
            <><DatabaseOutlined /> 后端</>
          )}
        </Tag>
      </Tooltip>
      <Switch
        size="small"
        checked={!isDirect}
        checkedChildren="后端"
        unCheckedChildren="直连"
        onChange={(checked) => {
          const newMode: DataSourceMode = checked ? "backend" : "direct";
          setDataSourceMode(newMode);
          setMode(newMode);
          message.success(
            `已切换至：${newMode === "direct" ? "🔥 前端直连模式" : "💾 后端接口模式"}`,
            1.5,
          );
          setTimeout(() => window.location.reload(), 400);
        }}
      />
    </div>
  );
}
