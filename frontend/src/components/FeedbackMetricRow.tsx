import { Card, Col, Row } from "antd";
import type { FeedbackSummary } from "../api";
import { Paragraph, Text, Title } from "../workspace/shared";

export function FeedbackMetricRow({ summary }: { summary: FeedbackSummary }) {
  return (
    <Row gutter={[12, 12]} className="feedbackMetricRow">
      <Col xs={12} lg={6}>
        <Card size="small" className="runRecordMetricCard feedbackMetricCard">
          <Text type="secondary">待处理</Text>
          <Title level={3}>{summary.open}</Title>
        </Card>
      </Col>
      <Col xs={12} lg={6}>
        <Card size="small" className="runRecordMetricCard feedbackMetricCard">
          <Text type="secondary">已完成</Text>
          <Title level={3}>{summary.completed}</Title>
        </Card>
      </Col>
      <Col xs={12} lg={6}>
        <Card size="small" className="runRecordMetricCard feedbackMetricCard">
          <Text type="secondary">反馈总数</Text>
          <Title level={3}>{summary.total}</Title>
        </Card>
      </Col>
      <Col xs={12} lg={6}>
        <Card size="small" className="runRecordMetricCard feedbackMetricCard">
          <Text type="secondary">完成率</Text>
          <Title level={3}>{summary.total ? Math.round((summary.completed / summary.total) * 100) : 0}%</Title>
        </Card>
      </Col>
    </Row>
  );
}
