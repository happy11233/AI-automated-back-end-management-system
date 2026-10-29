import React from "react";
import { Paragraph, Text, Title } from "../workspace/shared";

export function DetailText({ label, value, mono = false }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="customerInboxDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "aiWorkflowMono" : "aiWorkflowText"}>{value}</Text>
    </div>
  );
}
