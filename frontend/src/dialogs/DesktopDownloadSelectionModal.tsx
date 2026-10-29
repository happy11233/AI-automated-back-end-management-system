import { AppleOutlined, DesktopOutlined } from "@ant-design/icons";
import { Col, Modal, Row, Space, Tag } from "antd";
import type { DesktopDownloadItem, DesktopPlatform } from "../api";
import { Paragraph, Text, Title } from "../workspace/shared";

export function DesktopDownloadSelectionModal({
  open,
  downloads,
  loading,
  downloadingPlatform,
  onCancel,
  onSelectPlatform,
}: {
  open: boolean;
  downloads: DesktopDownloadItem[];
  loading: boolean;
  downloadingPlatform: DesktopPlatform | "";
  onCancel: () => void;
  onSelectPlatform: (platform: DesktopPlatform) => void;
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

  return (
    <Modal
      open={open}
      title="选择桌面端版本"
      onCancel={onCancel}
      footer={null}
      width={720}
      centered
      destroyOnHidden
      className="desktopDownloadModal"
    >
      <Space direction="vertical" size={14} style={{ width: "100%" }}>
        <Text type="secondary">先选择 macOS，再直接下载对应安装包。</Text>
        <Row gutter={[12, 12]}>
          {resolvedDownloads.map((item) => (
            <Col xs={24} md={12} key={item.platform}>
              <button
                type="button"
                className={`desktopDownloadChoice ${item.available ? "available" : "unavailable"}`}
                disabled={!item.available || loading || downloadingPlatform === item.platform}
                onClick={() => onSelectPlatform(item.platform)}
              >
                <div className="desktopDownloadChoiceInner">
                  <div className="desktopDownloadChoiceHeader">
                    <div className="desktopDownloadChoiceIcon">
                      {item.platform === "mac" ? <AppleOutlined /> : <DesktopOutlined />}
                    </div>
                    <div className="desktopDownloadChoiceTitleWrap">
                      <Title level={4} className="desktopDownloadChoiceTitle">{item.label}</Title>
                      <Text type="secondary">
                        {item.available ? "点击后直接下载" : "当前没有可用安装包"}
                      </Text>
                    </div>
                  </div>
                  <div className="desktopDownloadChoiceMeta">
                    <Tag color={item.available ? "green" : "default"}>
                      {item.available ? "可下载" : "未发布"}
                    </Tag>
                    <Text type="secondary">{item.filename || "等待上传"}</Text>
                  </div>
                </div>
              </button>
            </Col>
          ))}
        </Row>
      </Space>
    </Modal>
  );
}
