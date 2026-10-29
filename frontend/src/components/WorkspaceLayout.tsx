import type { ComponentProps } from "react";
import { PageContainer, ProConfigProvider, ProLayout } from "@ant-design/pro-components";

export function WorkspaceLayout(props: ComponentProps<typeof ProLayout>) {
  return (
    <ProConfigProvider hashed={false}>
      <ProLayout {...props} />
    </ProConfigProvider>
  );
}

export function WorkspacePage(props: ComponentProps<typeof PageContainer>) {
  return <PageContainer {...props} />;
}
