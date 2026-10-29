import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Empty, Modal, Spin, Tag, Typography } from 'antd';
import { ApiOutlined, ArrowRightOutlined, ClockCircleOutlined, RadarChartOutlined } from '@ant-design/icons';
import { analyzeCompetitorPrices, getCompetitorMonitor, type CompetitorMonitorData, type CompetitorProduct, type CompetitorSnapshot } from '../api';
import './competitor-monitor.css';

const { Title, Paragraph, Text } = Typography;
const displayTime = (value: string) => new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
const money = (cents: number) => new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'USD' }).format(cents / 100);

function PriceHistory({ product, history }: { product: CompetitorProduct; history: CompetitorSnapshot[] }) {
  const points = history.flatMap(snapshot => {
    const item = snapshot.products.find(item => item.sku === product.sku);
    return item ? [{ at: snapshot.captured_at, own: item.own_price_cents, competitor: item.lowest_competitor_cents }] : [];
  });
  if (points.length < 2) return <p className="competitorHistoryHint">完成两次分析后显示实际采集趋势</p>;
  const values = points.flatMap(point => [point.own, point.competitor]);
  const low = Math.min(...values) * 0.94, high = Math.max(...values) * 1.06;
  const first = Date.parse(points[0].at), last = Date.parse(points[points.length - 1].at);
  const x = (index: number) => 18 + (last > first ? (Date.parse(points[index].at) - first) / (last - first) : index / (points.length - 1)) * 424;
  const y = (value: number) => 92 - (value - low) / (high - low) * 76;
  return <div className="competitorHistory">
    <div className="competitorHistoryLegend"><span>最近 {points.length} 次采集趋势</span><span><i />自家 <i className="competitorDot" />竞品最低</span></div>
    <svg viewBox="0 0 460 112" role="img" aria-label={product.name + '自家与竞品最低价格趋势'}>
      {[24, 58, 92].map(line => <line key={line} x1="18" x2="442" y1={line} y2={line} stroke="#e9edf5" strokeDasharray="3 4" />)}
      {(['own', 'competitor'] as const).map(key => <g key={key}>
        <polyline fill="none" stroke={key === 'own' ? '#5268e8' : '#18a693'} strokeWidth="2.5" points={points.map((point, i) => x(i) + ',' + y(point[key])).join(' ')} />
        {points.map((point, i) => <circle key={point.at} cx={x(i)} cy={y(point[key])} r="3" fill={key === 'own' ? '#5268e8' : '#18a693'}><title>{displayTime(point.at)} · {key === 'own' ? '自家' : '竞品最低'} {money(point[key])}</title></circle>)}
      </g>)}
    </svg>
    <div className="competitorHistoryTimes"><span>{displayTime(points[0].at)}</span><span>{displayTime(points[points.length - 1].at)}</span></div>
  </div>;
}

function PriceComparison({ product, history }: { product: CompetitorProduct; history: CompetitorSnapshot[] }) {
  const max = Math.max(product.own_price_cents, ...product.competitors.map(item => item.price_cents)) * 1.12;
  const rows = [{ id: product.sku, name: '自家商品', price_cents: product.own_price_cents, heat_score: null }, ...product.competitors];
  return <Card className="competitorProduct">
    <div className="competitorProductHeading"><div><Title level={4}>{product.name}</Title><Text type="secondary">{product.specification}</Text></div><span className="competitorCurrency">USD</span></div>
    <figure className="competitorBars" aria-label={product.name + '自家商品与热点竞品价格对比'}>
      {rows.map((item, index) => <div className="competitorBarRow" key={item.id}>
        <div className="competitorBarLabel"><span>{item.name}</span>{item.heat_score !== null && <small>模拟热度 {item.heat_score}</small>}</div>
        <div className="competitorBarTrack"><div className={'competitorBarFill ' + (index === 0 ? 'own' : '')} style={{ width: (item.price_cents / max * 100) + '%' }} /></div>
        <strong>{money(item.price_cents)}</strong>
      </div>)}
      <figcaption>条形长度从零起算 · 竞品按模拟热度排序</figcaption>
    </figure>
    <div className={'competitorPriceGap ' + (product.gap_cents > 0 ? 'higher' : 'lower')}>
      较竞品最低价{product.gap_cents > 0 ? '高' : product.gap_cents < 0 ? '低' : '持平'}
      {product.gap_cents !== 0 && <> <strong>{money(Math.abs(product.gap_cents))}</strong><span>（{Math.abs(product.gap_percent).toFixed(1)}%）</span></>}
    </div>
    <PriceHistory product={product} history={history} />
  </Card>;
}

export function CompetitorMonitor({ token, role, onNavigate }: { token: string; role: 'admin' | 'employee'; onNavigate: (view: string) => void }) {
  const [data, setData] = useState<CompetitorMonitorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [apiOpen, setApiOpen] = useState(false);
  const sequence = useRef(0);
  const alive = useRef(true);
  const analyzingRef = useRef(false);

  useEffect(() => {
    alive.current = true;
    const refresh = async () => {
      if (analyzingRef.current) return;
      const id = ++sequence.current;
      try {
        const result = await getCompetitorMonitor(token);
        if (alive.current && id === sequence.current) { setData(result); setError(''); }
      } catch (cause) {
        if (alive.current && id === sequence.current) setError(cause instanceof Error ? cause.message : '监控结果加载失败');
      } finally {
        if (alive.current && id === sequence.current) setLoading(false);
      }
    };
    void refresh();
    const timer = window.setInterval(() => { if (document.visibilityState === 'visible') void refresh(); }, 15000);
    return () => { alive.current = false; sequence.current++; window.clearInterval(timer); };
  }, [token]);

  const analyze = async () => {
    if (analyzingRef.current) return;
    analyzingRef.current = true;
    sequence.current++;
    setAnalyzing(true); setError('');
    try {
      const snapshot = await analyzeCompetitorPrices(token);
      if (!alive.current) return;
      // Render the saved analysis immediately, even if a subsequent status refresh fails.
      setData(previous => previous ? { ...previous, latest: snapshot, history: [...previous.history.filter(item => item.id !== snapshot.id), snapshot].slice(-28) } : {
        provider: 'mock', latest: snapshot, history: [snapshot],
        schedule: { timezone: 'Asia/Shanghai', times: ['08:00', '11:00', '14:00', '16:00'], next_run_at: null, completed_today: 0, scheduler_healthy: false, status_label: '后台调度待就绪' },
        official_api: { status: 'not_connected', label: '官方开放 API 尚未接入' },
      });
      try {
        const result = await getCompetitorMonitor(token);
        if (alive.current) setData(result);
      } catch {
        if (alive.current) setError('分析结果已保存，巡检状态暂未刷新，稍后自动重试。');
      }
    } catch (cause) {
      if (alive.current) setError(cause instanceof Error ? cause.message : '分析失败，请重新开始');
    } finally {
      analyzingRef.current = false;
      if (alive.current) { setAnalyzing(false); setLoading(false); }
    }
  };
  const latest = data?.latest;
  return <div className="competitorMonitor">
    <section className="competitorHero">
      <div><span className="competitorEyebrow"><RadarChartOutlined /> 商品与竞品监控 AGENT</span><Title level={2}>运营竞品分析</Title><Paragraph>关注价格变化，把重复比价交给 Agent。</Paragraph><Tag color="gold">MOCK · 模拟数据</Tag></div>
      <div className="competitorActions"><Button aria-label="开始分析" type="primary" size="large" loading={analyzing} onClick={() => void analyze()} icon={<RadarChartOutlined />}>{analyzing ? '正在分析' : '开始分析'}</Button><Button aria-label="接入官方开放 API" type="text" icon={<ApiOutlined />} onClick={() => setApiOpen(true)}>接入官方开放 API <ArrowRightOutlined /></Button></div>
    </section>
    <section className="competitorSchedule" aria-label="自动巡检计划">
      <div><ClockCircleOutlined /><strong>每天自动巡检 4 次</strong><span>{(data?.schedule.times || ['08:00', '11:00', '14:00', '16:00']).join(' / ')} · 北京时间</span></div>
      <div><span className={'competitorStatusDot ' + (data?.schedule.scheduler_healthy ? 'online' : '')} /><Text type="secondary">{data?.schedule.status_label || '正在检查后台调度'}</Text><span>今日已完成 {data?.schedule.completed_today ?? '—'}/4</span></div>
      <div className="competitorScheduleNext">下次计划：{data?.schedule.next_run_at ? displayTime(data.schedule.next_run_at) : '等待状态同步'}{data && !data.schedule.scheduler_healthy && <span>需启动后台 worker 与 beat，关闭页面不影响已运行的后台巡检</span>}</div>
    </section>
    {error && <Alert type="error" showIcon message={latest ? '当前展示最近一次成功结果' : '监控暂不可用'} description={error} />}
    {loading && !latest ? <div className="competitorEmpty"><Spin tip="正在读取监控结果" size="large"><div style={{ height: 80 }} /></Spin></div> : latest ? <>
      <div className="competitorResultHeader"><div><Title level={3}>价格对比</Title><Text type="secondary">最近{latest.trigger_type === 'schedule' ? '自动巡检' : '手动分析'} · {displayTime(latest.captured_at)}</Text></div><span>{latest.summary.product_count} 件自家商品 <span className="competitorDivider">/</span> {latest.summary.competitor_count} 个模拟热点竞品</span></div>
      <div className="competitorProductGrid">{latest.products.map(product => <PriceComparison key={product.sku} product={product} history={data!.history} />)}</div>
      <p className="competitorNotice">{latest.notice} 本页仅监控与比较，不执行商品调价。</p>
    </> : <Card className="competitorEmpty"><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={error ? '暂未读取到分析结果' : '还没有价格对比结果'} /><Paragraph type="secondary">点击「开始分析」，或等待下一次后台巡检。完成后会展示自家商品与热点竞品的价格图表。</Paragraph></Card>}
    <Modal title="接入官方开放 API" open={apiOpen} onCancel={() => setApiOpen(false)} footer={role === 'admin' ? <Button type="primary" onClick={() => { setApiOpen(false); onNavigate('connectors'); }}>前往连接配置</Button> : <Button onClick={() => setApiOpen(false)}>知道了</Button>}>
      <Alert type="info" showIcon message="尚未接入 · 当前继续使用模拟数据" />
      <Paragraph className="competitorApiCopy">已保留价格采集适配器扩展点。正式接入需由管理员配置平台应用授权、店铺与站点，核验官方接口允许读取的价格字段，并建立自家 SKU 与竞品标识映射。</Paragraph>
      <Paragraph>热点来源、商品可比规格、币种、优惠与运费口径也需单独确认。当前连接配置用于检查现有连接器；完成授权和适配联调后才能切换为真实数据。</Paragraph>
      <Text type="secondary">{role === 'employee' ? '请联系管理员处理授权。' : '请勿在对话或页面中粘贴 API 密钥。'}</Text>
    </Modal>
  </div>;
}
