# 财务工资表导出 Skill

## 适用场景

财务用户明确要求导出员工工资表、工资单或薪资 Excel，并能从自然语言中识别期间。

典型触发：

- 把这个月所有员工的工资表导出 Excel。
- 生成 2026 年 7 月工资单。
- 下载上个月薪资明细。

## 不适用场景

- 用户只说“导出 Excel 表”，必须先追问表类型。
- 用户询问工资表怎么导出，应优先走 RAG。
- 运营或客服岗位请求工资数据，应由权限闸门拒绝。

## 权限规则

- 仅财务岗位或管理员可执行。
- 非管理员必须启用 `automation-salary_summary`。
- ERP 资源只能是 `Salary Slip`。
- 工资数据属于高风险敏感数据，导出结果必须保留人工复核口径。

## 执行步骤

1. 校验岗位、AI 应用启用状态和 ERP 资源范围。
2. 使用 `recognize_salary_export_intent(...)` 识别工资导出意图和期间。
3. 查询真实 ERP `Salary Slip`。
4. 使用 `export_salary_workbook_from_erp(...)` 生成工资 Excel。
5. 保存 generated file 产物。
6. 写入运行记录、步骤和审计。

## 输出格式

- 工资 Excel 文件。
- 期间、员工数、gross/net 合计。
- 意图识别结果和置信度。
- ERP provider 和资源摘要。
- 运行记录 ID。

## 安全边界

ReAct 误判不能直接触发工资导出。低置信度、模糊 Excel、跨岗位和 ERP 资源越界必须在 Skill Executor 前被阻断。
