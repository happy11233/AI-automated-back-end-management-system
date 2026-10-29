import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Empty, Segmented, Tabs, Tooltip, type TabsProps } from "antd";
import {
  aggregateTrend,
  chartMaximum,
  safeChartNumber,
  trendTimeDomain,
  type TrendDatum,
} from "./chartData";

export const chartColors = {
  blue: "#2563eb",
  green: "#059669",
  amber: "#d97706",
  purple: "#7c3aed",
  red: "#dc2626",
  gray: "#64748b",
};

export function WorkspaceTabs({
  items,
  defaultKey,
  storageKey,
}: {
  items: NonNullable<TabsProps["items"]>;
  defaultKey?: string;
  storageKey: string;
}) {
  const fallback = defaultKey || items[0]?.key || "";
  const readTab = () => {
    const key = new URLSearchParams(window.location.search).get(storageKey);
    return items.some((item) => item.key === key) ? key! : fallback;
  };
  const [activeKey, setActiveKey] = useState(readTab);
  useEffect(() => {
    const sync = () => setActiveKey(readTab());
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, [storageKey, fallback]);
  return (
    <Tabs
      className="workspaceSectionTabs"
      activeKey={activeKey}
      onChange={(key) => {
        setActiveKey(key);
        const url = new URL(window.location.href);
        url.searchParams.set(storageKey, key);
        window.history.replaceState(window.history.state, "", url);
      }}
      items={items}
    />
  );
}

type Series = { key: string; label: string; color: string };

export function TrendChart({
  data,
  series,
  label,
  unit = "次",
}: {
  data: TrendDatum[];
  series: Series[];
  label: string;
  unit?: string;
}) {
  const id = useId();
  const container = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(900);
  const [mode, setMode] = useState<"bar" | "line">("bar");
  const [selected, setSelected] = useState<number | null>(null);
  const points = aggregateTrend(data, 30);
  const domain = trendTimeDomain(points);
  const maximum = chartMaximum(
    points.flatMap((point) =>
      series.map((item) => safeChartNumber(point.values[item.key])),
    ),
  );
  const width = chartWidth,
    height = 280,
    left = 48,
    right = 20,
    top = 18,
    bottom = 42;
  const dateTickCount = domain
    ? Math.min(
        width < 480 ? 3 : 5,
        Math.round(
          (points[points.length - 1].endTimestamp! - points[0].timestamp!) /
            86_400_000,
        ) + 1,
      )
    : 0;
  const plotWidth = width - left - right,
    plotHeight = height - top - bottom;
  const timeX = (time: number) =>
    left + ((time - domain!.start) / (domain!.end - domain!.start)) * plotWidth;
  const x = (index: number) =>
    domain
      ? timeX((points[index].timestamp! + points[index].endTimestamp!) / 2)
      : left + ((index + 0.5) / Math.max(points.length, 1)) * plotWidth;
  const y = (value: number) =>
    top + plotHeight * (1 - safeChartNumber(value) / maximum);
  const active = selected === null ? undefined : points[selected];
  const number = (value: number) =>
    value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) =>
      setChartWidth(Math.max(260, Math.min(900, entry.contentRect.width))),
    );
    if (container.current) observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  return (
    <div className="workspaceChart" ref={container}>
      <div className="workspaceChartToolbar">
        <span className="workspaceChartUnit">
          单位：{unit}
          {data.length > 30
            ? ` · 每 ${Math.ceil(data.length / 30)} 个有记录日期汇总`
            : ""}
        </span>
        <Segmented
          size="small"
          aria-label={`${label}图表类型`}
          value={mode}
          onChange={(value) => setMode(value as typeof mode)}
          options={[
            { label: "柱状图", value: "bar" },
            { label: "折线图", value: "line" },
          ]}
        />
      </div>
      {!points.length ? (
        <Empty description="暂无趋势数据" />
      ) : (
        <>
          <svg
            className="workspaceTrendSvg"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-labelledby={id}
          >
            <title id={id}>
              {label}，{points.length} 个时间区间，单位{unit}
            </title>
            {[0, 1, 2, 3, 4].map((tick) => {
              const value = (maximum * tick) / 4;
              return (
                <g key={tick}>
                  <line
                    x1={left}
                    x2={width - right}
                    y1={y(value)}
                    y2={y(value)}
                    stroke="#e8edf5"
                    strokeDasharray={tick ? "4 4" : undefined}
                  />
                  <text
                    x={left - 10}
                    y={y(value) + 4}
                    textAnchor="end"
                    className="workspaceAxisText"
                  >
                    {number(value)}
                  </text>
                </g>
              );
            })}
            {domain &&
              Array.from({ length: dateTickCount }, (_, index) => {
                const first = points[0].timestamp!,
                  last = points[points.length - 1].endTimestamp!;
                if (first === last && index > 0) return null;
                const time =
                  first +
                  Math.round(
                    ((last - first) * index) /
                      Math.max(1, dateTickCount - 1) /
                      86_400_000,
                  ) *
                    86_400_000;
                return (
                  <text
                    key={index}
                    x={timeX(time)}
                    y={height - 16}
                    textAnchor="middle"
                    className="workspaceAxisText"
                  >
                    {new Date(time).toISOString().slice(5, 10)}
                  </text>
                );
              })}
            {series.map((item) =>
              mode === "line" ? (
                <polyline
                  key={item.key}
                  fill="none"
                  stroke={item.color}
                  strokeWidth="2.5"
                  strokeLinejoin="round"
                  points={points
                    .map(
                      (point, index) =>
                        `${x(index)},${y(point.values[item.key])}`,
                    )
                    .join(" ")}
                />
              ) : null,
            )}
            {points.map((point, index) => {
              const stride = Math.max(1, Math.ceil(points.length / 7));
              const groupWidth = domain
                ? ((plotWidth *
                    (point.endTimestamp! - point.timestamp! + 86_400_000)) /
                    (domain.end - domain.start)) *
                  0.72
                : (plotWidth / points.length) * 0.72;
              const barWidth = Math.min(26, groupWidth / series.length);
              const description = `${point.label}：${series.map((item) => `${item.label} ${number(safeChartNumber(point.values[item.key]))}${unit}`).join("，")}`;
              return (
                <g
                  key={`${point.label}-${index}`}
                  tabIndex={0}
                  role="img"
                  aria-label={description}
                  className="workspaceChartPoint"
                  onMouseEnter={() => setSelected(index)}
                  onMouseLeave={() => setSelected(null)}
                  onFocus={() => setSelected(index)}
                  onBlur={() => setSelected(null)}
                >
                  <title>{description}</title>
                  <rect
                    x={x(index) - Math.max(groupWidth, 16) / 2}
                    y={top}
                    width={Math.max(groupWidth, 16)}
                    height={plotHeight}
                    fill={selected === index ? "#2563eb08" : "transparent"}
                  />
                  {series.map((item, seriesIndex) => {
                    const value = safeChartNumber(point.values[item.key]);
                    return mode === "bar" ? (
                      <rect
                        key={item.key}
                        data-series={item.key}
                        data-value={value}
                        x={
                          x(index) -
                          (barWidth * series.length) / 2 +
                          seriesIndex * barWidth
                        }
                        y={y(value)}
                        width={Math.max(1, barWidth - 2)}
                        height={(plotHeight * value) / maximum}
                        rx="3"
                        fill={item.color}
                        pointerEvents="none"
                      />
                    ) : (
                      <circle
                        key={item.key}
                        cx={x(index)}
                        cy={y(value)}
                        r={selected === index || points.length === 1 ? 4 : 2}
                        fill={item.color}
                        pointerEvents="none"
                      />
                    );
                  })}
                  {!domain &&
                    (index % stride === 0 || index === points.length - 1) && (
                      <text
                        x={x(index)}
                        y={height - 16}
                        textAnchor="middle"
                        className="workspaceAxisText"
                      >
                        {point.shortLabel || point.label}
                      </text>
                    )}
                </g>
              );
            })}
          </svg>
          {domain && (
            <div className="workspaceChartUnit">
              按实际日期间隔展示；无记录日期留空。
            </div>
          )}
          <div className="workspaceChartReadout" aria-live="polite">
            {active ? (
              <>
                <strong>{active.label}</strong>
                {series.map((item) => (
                  <span key={item.key}>
                    <i style={{ background: item.color }} />
                    {item.label}{" "}
                    {number(safeChartNumber(active.values[item.key]))}
                    {unit}
                  </span>
                ))}
              </>
            ) : (
              <span>悬停或使用键盘聚焦，查看具体数值</span>
            )}
          </div>
        </>
      )}
      <div className="workspaceChartLegend">
        {series.map((item) => (
          <span key={item.key}>
            <i style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function RankingChart({
  items,
  label,
  unit = "次",
  percent = false,
}: {
  items: Array<{
    key: string;
    label: string;
    value: number;
    color?: string;
    detail?: ReactNode;
  }>;
  label: string;
  unit?: string;
  percent?: boolean;
}) {
  const maximum = percent
    ? 100
    : Math.max(1, ...items.map((item) => safeChartNumber(item.value)));
  if (!items.length) return <Empty description="暂无可展示数据" />;
  return (
    <div className="workspaceRanking" role="list" aria-label={label}>
      {items.map((item, index) => {
        const value = safeChartNumber(item.value);
        const formatted = `${value.toLocaleString("zh-CN", { maximumFractionDigits: percent ? 1 : 2 })}${unit}`;
        return (
          <div className="workspaceRankingItem" role="listitem" key={item.key}>
            <div className="workspaceRankingHeading">
              <Tooltip title={item.label}>
                <span className="workspaceRankingLabel">
                  <small>{String(index + 1).padStart(2, "0")}</small>
                  {item.label}
                </span>
              </Tooltip>
              <strong>{formatted}</strong>
            </div>
            <div
              className="workspaceRankingTrack"
              role="meter"
              aria-label={item.label}
              aria-valuenow={value}
              aria-valuemin={0}
              aria-valuemax={Math.max(maximum, value)}
            >
              <span
                style={{
                  width: `${Math.min(100, (value / maximum) * 100)}%`,
                  background: item.color || chartColors.blue,
                }}
              />
            </div>
            {item.detail && (
              <div className="workspaceRankingDetail">{item.detail}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function DistributionChart({
  items,
  label,
}: {
  items: Array<{ key: string; label: string; value: number; color: string }>;
  label: string;
}) {
  const total = items.reduce(
    (sum, item) => sum + safeChartNumber(item.value),
    0,
  );
  if (!total) return <Empty description="暂无分布数据" />;
  return (
    <div className="workspaceDistribution" aria-label={label}>
      <div className="workspaceDistributionTotal">
        <strong>{total.toLocaleString("zh-CN")}</strong>
        <span>总记录</span>
      </div>
      <div className="workspaceDistributionBar">
        {items
          .filter((item) => item.value > 0)
          .map((item) => (
            <Tooltip
              key={item.key}
              title={`${item.label} ${item.value} 次 · ${((item.value / total) * 100).toFixed(1)}%`}
            >
              <span
                style={{
                  width: `${(item.value / total) * 100}%`,
                  background: item.color,
                }}
                aria-label={`${item.label} ${item.value}次`}
              />
            </Tooltip>
          ))}
      </div>
      <div className="workspaceDistributionLegend">
        {items.map((item) => (
          <div key={item.key}>
            <span>
              <i style={{ background: item.color }} />
              {item.label}
            </span>
            <strong>
              {safeChartNumber(item.value).toLocaleString("zh-CN")}
            </strong>
            <small>
              {((safeChartNumber(item.value) / total) * 100).toFixed(1)}%
            </small>
          </div>
        ))}
      </div>
    </div>
  );
}
