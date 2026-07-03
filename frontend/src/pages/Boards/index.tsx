/** Industry / concept boards page. */

import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Tag, Drawer, List, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { fetchBoards, fetchBoardMembers } from "@/services/stock";
import type { BoardInfo, BoardMember } from "@/services/typings";
import type { ProColumns } from "@ant-design/pro-components";

export default function BoardsPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [members, setMembers] = useState<BoardMember[]>([]);
  const [boardName, setBoardName] = useState("");
  const [membersLoading, setMembersLoading] = useState(false);
  const [allBoards, setAllBoards] = useState<BoardInfo[]>([]);

  // Load all boards once for dropdown options (fetch all pages)
  useEffect(() => {
    async function loadAll() {
      let all: BoardInfo[] = [];
      let page = 1;
      const pageSize = 200;
      while (true) {
        const res = await fetchBoards({ page, page_size: pageSize });
        all = [...all, ...res.items];
        if (all.length >= res.total) break;
        page++;
      }
      setAllBoards(all);
    }
    loadAll();
  }, []);

  // Derive unique codes and names for dropdowns
  const codeEnum = useMemo(() => {
    const map: Record<string, { text: string }> = {};
    allBoards.forEach((b) => {
      if (!map[b.board_code]) map[b.board_code] = { text: b.board_code };
    });
    return map;
  }, [allBoards]);

  const nameEnum = useMemo(() => {
    const map: Record<string, { text: string }> = {};
    allBoards.forEach((b) => {
      if (!map[b.board_name]) map[b.board_name] = { text: b.board_name };
    });
    return map;
  }, [allBoards]);

  const columns: ProColumns<BoardInfo>[] = [
    {
      title: "板块代码",
      dataIndex: "board_code",
      key: "board_code",
      width: 120,
      valueType: "select",
      valueEnum: codeEnum,
      fieldProps: { showSearch: true, allowClear: true },
    },
    {
      title: "板块名称",
      dataIndex: "board_name",
      key: "board_name",
      width: 200,
      valueType: "select",
      valueEnum: nameEnum,
      fieldProps: { showSearch: true, allowClear: true },
    },
    {
      title: "类型",
      dataIndex: "board_type",
      key: "board_type",
      width: 100,
      valueType: "select",
      valueEnum: {
        industry: { text: "行业" },
        concept: { text: "概念" },
      },
      render: (_, row) => (
        <Tag color={row.board_type === "industry" ? "blue" : "orange"}>
          {row.board_type === "industry" ? "行业" : "概念"}
        </Tag>
      ),
    },
    {
      title: "数据源",
      dataIndex: "source",
      key: "source",
      width: 80,
      valueType: "select",
      valueEnum: {
        em: { text: "东方财富" },
        ths: { text: "同花顺" },
      },
    },
  ];

  const loadMembers = async (boardId: string, name: string) => {
    setBoardName(name);
    setDrawerOpen(true);
    setMembersLoading(true);
    try {
      const res = await fetchBoardMembers(boardId);
      setMembers(res.items);
    } finally {
      setMembersLoading(false);
    }
  };

  return (
    <PageContainer>
      <ProTable<BoardInfo>
        columns={columns}
        rowKey="id"
        request={async (params: Record<string, any>) => {
          const { current, pageSize, board_type, board_code, board_name } =
            params;
          const res = await fetchBoards({
            page: current,
            page_size: pageSize,
            board_type,
          });
          // Client-side filter for dropdown selections
          let items = res.items;
          let total = res.total;
          if (board_code) {
            items = items.filter((b) => b.board_code === board_code);
            total = items.length;
          }
          if (board_name) {
            items = items.filter((b) => b.board_name === board_name);
            total = items.length;
          }
          return {
            data: items,
            total,
            success: true,
          };
        }}
        search={{ labelWidth: "auto", defaultCollapsed: false }}
        onRow={(record) => ({
          onClick: () => loadMembers(record.id, record.board_name),
          style: { cursor: "pointer" },
        })}
        pagination={{ defaultPageSize: 30 }}
      />

      <Drawer
        title={`${boardName} — 成分股`}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={400}
        loading={membersLoading}
      >
        <List
          dataSource={members}
          renderItem={(item) => (
            <List.Item>
              <Typography.Text copyable={{ text: item.stock_code }}>
                {item.stock_code}
              </Typography.Text>
              <Typography.Text style={{ marginLeft: 12 }}>
                {item.stock_name || "-"}
              </Typography.Text>
            </List.Item>
          )}
        />
      </Drawer>
    </PageContainer>
  );
}
