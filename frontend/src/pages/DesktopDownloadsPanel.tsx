import { AppleOutlined, DesktopOutlined, DownloadOutlined } from "@ant-design/icons";
import { Button, Card, Col, Row, Space } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { DesktopDownloadItem } from "../api";
import { Paragraph, Text, Title, formatBytes } from "../workspace/shared";

export function DesktopDownloadsPanel({
  downloads,
  loading,
  openSelector,
}: {
  downloads: DesktopDownloadItem[];
  loading: boolean;
  openSelector: () => void;
}) {
  const fallbackDownloads: DesktopDownloadItem[] = [
    {
      platform: "mac",
      label: "macOS 版",
      available: false,
      filename: null,
      download_path: "/desktop-downloads/mac/download",
      size_bytes: null,
      updated_at: null,
    },
  ];
  const resolvedDownloads = fallbackDownloads.map((fallback) => (
    downloads.find((item) => item.platform === fallback.platform) || fallback
  ));
  const availableCount = resolvedDownloads.filter((item) => item.available).length;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard
        title="桌面端下载"
        subTitle="先选择平台，再直接下载对应安装包"
        bordered
        extra={
          <Button type="primary" icon={<DownloadOutlined />} onClick={openSelector}>
            选择平台
          </Button>
        }
      >
        <Row gutter={[12, 12]}>
          <Col xs={24} md={8}>
            <Card size="small" className="contextCard dashboardStatCard">
              <div className="dashboardCenteredMetric">
                <Text type="secondary" className="dashboardMetricTitle">可下载平台</Text>
                <Title level={3} className="dashboardMetricValue">{availableCount}</Title>
                <Text type="secondary">已准备好下载的版本</Text>
              </div>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" className="contextCard dashboardStatCard">
              <div className="dashboardCenteredMetric">
                <Text type="secondary" className="dashboardMetricTitle">平台总数</Text>
                <Title level={3} className="dashboardMetricValue">{resolvedDownloads.length}</Title>
                <Text type="secondary">当前仅显示 macOS</Text>
              </div>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" className="contextCard dashboardStatCard">
              <div className="dashboardCenteredMetric">
                <Text type="secondary" className="dashboardMetricTitle">下载方式</Text>
                <Title level={3} className="dashboardMetricValue">弹窗选择</Title>
                <Text type="secondary">选完平台后直接触发下载</Text>
              </div>
            </Card>
          </Col>
        </Row>
      </ProCard>

      <ProCard title="平台列表" bordered loading={loading}>
        <Row gutter={[12, 12]}>
          {resolvedDownloads.map((item) => (
            <Col xs={24} md={12} key={item.platform}>
              <Card size="small" className={`contextCard desktopDownloadCard ${item.available ? "available" : "unavailable"}`}>
                <div className="desktopDownloadCardInner">
                  <div className="desktopDownloadCardHeader">
                    <div className="desktopDownloadCardIcon">
                      {item.platform === "mac" ? <AppleOutlined /> : <DesktopOutlined />}
                    </div>
                    <div className="desktopDownloadCardTitleWrap">
                      <Title level={4} className="desktopDownloadCardTitle">{item.label}</Title>
                      <Text type="secondary">
                        {item.available ? "已准备好安装包" : "暂未找到对应安装包"}
                      </Text>
                    </div>
                  </div>
                  <div className="desktopDownloadCardMeta">
                    <div>
                      <Text type="secondary">文件名</Text>
                      <Text strong>{item.filename || "等待上传"}</Text>
                    </div>
                    <div>
                      <Text type="secondary">大小</Text>
                      <Text strong>{formatBytes(item.size_bytes)}</Text>
                    </div>
                    <div>
                      <Text type="secondary">更新时间</Text>
                      <Text strong>{formatDateTime(item.updated_at)}</Text>
                    </div>
                  </div>
                  <Button
                    type="primary"
                    icon={<DownloadOutlined />}
                    disabled={!item.available}
                    onClick={openSelector}
                  >
                    选择后下载
                  </Button>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </ProCard>
    </Space>
  );
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
