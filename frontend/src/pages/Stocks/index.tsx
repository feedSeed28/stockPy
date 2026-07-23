/** A-stock list page with search, filter, and pagination. */

import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Tag } from "antd";
import { fetchStocks } from "@/services/stock";
import type { StockInfo } from "@/services/typings";
import type { ProColumns } from "@ant-design/pro-components";

const exchangeColor: Record<string, string> = {
  SH: "red",
  SZ: "green",
  BJ: "blue",
};

const columns: ProColumns<StockInfo>[] = [
  {
    title: "代码",
    dataIndex: "code",
    key: "code",
    width: 100,
    copyable: true,
  },
  {
    title: "名称",
    dataIndex: "name",
    key: "name",
    width: 120,
  },
  {
    title: "交易所",
    dataIndex: "exchange",
    key: "exchange",
    width: 90,
    valueType: "select",
    valueEnum: {
      SH: { text: "上海" },
      SZ: { text: "深圳" },
      BJ: { text: "北京" },
    },
    render: (_, row) => (
      <Tag color={exchangeColor[row.exchange] || "default"}>{row.exchange}</Tag>
    ),
  },
  {
    title: "板块",
    dataIndex: "board_type",
    key: "board_type",
    width: 90,
    valueType: "select",
    valueEnum: {
      "主板": { text: "主板" },
      "科创板": { text: "科创板" },
      "创业板": { text: "创业板" },
      "北交所": { text: "北交所" },
    },
    render: (_, row) => row.board_type || "-",
  },
  {
    title: "行业",
    dataIndex: "industry",
    key: "industry",
    width: 150,
    ellipsis: true,
    search: false,
  },
  {
    title: "状态",
    dataIndex: "is_active",
    key: "is_active",
    width: 80,
    valueType: "select",
    valueEnum: {
      true: { text: "上市" },
      false: { text: "退市" },
    },
    render: (_, row) =>
      row.is_active ? (
        <Tag color="green">上市</Tag>
      ) : (
        <Tag color="red">退市</Tag>
      ),
  },
];

export default function StocksPage() {
  return (
    <PageContainer>
      <ProTable<StockInfo>
        columns={columns}
        rowKey="code"
        request={async (params: Record<string, any>) => {
          const { current, pageSize, exchange, board_type, keyword, is_active } =
            params;
          const res = await fetchStocks({
            page: current,
            page_size: pageSize,
            exchange,
            board_type,
            is_active: is_active === undefined ? true : is_active,
            keyword,
          });
          return {
            data: res.items,
            total: res.total,
            success: true,
          };
        }}
        search={{
          labelWidth: "auto",
          defaultCollapsed: false,
        }}
        onRow={(record) => ({
          onClick: () => window.location.assign(`/stocks/${record.code}`),
          style: { cursor: "pointer" },
        })}
        pagination={{ defaultPageSize: 30, showSizeChanger: true }}
        scroll={{ y: 500 }}
      />
    </PageContainer>
  );
}
