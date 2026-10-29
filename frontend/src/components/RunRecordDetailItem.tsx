import React from "react";
import { Paragraph, Text, Title } from "../workspace/shared";

export function RunRecordDetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="runRecordDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "runRecordMono" : "runRecordText"}>{value}</Text>
    </div>
  );
}
