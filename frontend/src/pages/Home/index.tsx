import { PageContainer } from "@ant-design/pro-components";
import { Card, Typography } from "antd";

const { Title, Paragraph } = Typography;

export default function HomePage() {
  return (
    <PageContainer>
      <Card>
        <Title level={3}>Stock Quant System</Title>
        <Paragraph>股票量化系统 — P0 骨架就绪 ✅</Paragraph>
      </Card>
    </PageContainer>
  );
}
