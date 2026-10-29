import { useEffect, useRef, useState } from "react";
import { ArrowRightOutlined, CloudUploadOutlined, DownloadOutlined, PictureOutlined, SendOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Spin, Typography, message } from "antd";
import { downloadGeneratedFile, generateProductScene, type ProductSceneResponse } from "../api";
import { downloadBlob } from "../workspace/shared";
import "./product-scene.css";

const { Text, Title } = Typography;
const { TextArea } = Input;
const MAX_SIZE = 10 * 1024 * 1024;
const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];

export function ProductScenePanel({ token, onNavigate }: { token: string; onNavigate: (view: "chat") => void }) {
  const [source, setSource] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState("");
  const [generatedUrl, setGeneratedUrl] = useState("");
  const [result, setResult] = useState<ProductSceneResponse | null>(null);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const busyRef = useRef(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (!source) return;
    const url = URL.createObjectURL(source);
    setSourceUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [source]);
  useEffect(() => () => { requestId.current += 1; }, []);
  useEffect(() => () => { if (generatedUrl) URL.revokeObjectURL(generatedUrl); }, [generatedUrl]);

  function selectFile(file?: File) {
    if (!file) return;
    if (!IMAGE_TYPES.includes(file.type) || file.size > MAX_SIZE) {
      message.error("仅支持 10 MB 内的 PNG、JPEG、WebP 图片");
      return;
    }
    requestId.current += 1;
    setSource(file);
    setResult(null);
    setGeneratedUrl("");
    setError("");
  }

  async function generate() {
    if (!source) return message.warning("请先上传商品白底图");
    if (!prompt.trim()) return message.warning("请输入希望生成的背景或场景");
    if (busyRef.current) return;
    busyRef.current = true;
    const id = ++requestId.current;
    setBusy(true);
    setError("");
    let next: ProductSceneResponse | null = null;
    try {
      next = await generateProductScene(token, source, prompt.trim());
      if (id !== requestId.current) return;
      setResult(next);
      const file = await downloadGeneratedFile(token, next.artifact_id);
      if (id !== requestId.current) return;
      setGeneratedUrl(URL.createObjectURL(file.blob));
      message.success("场景图已生成并保存");
    } catch (cause) {
      if (id === requestId.current) setError(next ? "图片已生成，但预览加载失败；请使用下载按钮重试" : cause instanceof Error ? cause.message : "图片生成失败");
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  async function download() {
    if (!result) return;
    try {
      const file = await downloadGeneratedFile(token, result.artifact_id);
      downloadBlob(file.blob, file.filename || result.filename);
    } catch (cause) {
      message.error(cause instanceof Error ? cause.message : "图片下载失败");
    }
  }

  return <div className="productScene">
    <div className="productSceneIntro">
      <div><span className="productSceneEyebrow">OPERATIONS · CREATIVE STUDIO</span><Title level={3}>把白底商品图变成真实场景</Title><Text type="secondary">上传原图，告诉 Agent 想要的氛围。生成后可直接预览、下载，并在文件中心留存。</Text></div>
      <Button icon={<SendOutlined />} onClick={() => onNavigate("chat")}>在 AI 对话中生成</Button>
    </div>
    <div className="productSceneGrid">
      <section className="productSceneCard" aria-label="原始商品图片与生成条件">
        <div className="productSceneCardHeading"><span className="productSceneStep">01</span><div><strong>商品原图</strong><small>上传白底图并添加场景提示词</small></div></div>
        <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={event => { selectFile(event.target.files?.[0]); event.target.value = ""; }} />
        <button type="button" className={"productSceneDrop " + (sourceUrl ? "hasImage" : "")} onClick={() => fileInput.current?.click()} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); selectFile(event.dataTransfer.files[0]); }}>
          {sourceUrl ? <img src={sourceUrl} alt="上传的商品原图" /> : <div className="productSceneEmpty"><CloudUploadOutlined /><strong>点击或拖拽上传商品白底图</strong><span>PNG / JPEG / WebP · 最大 10 MB</span></div>}
        </button>
        <div className="productSceneFileMeta"><Text type="secondary">{source ? source.name : "尚未选择图片"}</Text>{source && <Button type="link" onClick={() => fileInput.current?.click()}>更换图片</Button>}</div>
        <label className="productSceneLabel" htmlFor="scene-prompt">场景描述</label>
        <TextArea id="scene-prompt" value={prompt} onChange={event => setPrompt(event.target.value)} maxLength={1200} showCount autoSize={{ minRows: 4, maxRows: 8 }} placeholder="例如：把商品放在清晨阳光洒落的木质桌面上，背景是柔和的现代客厅，保持商品本身和包装文字不变。" />
        <Button type="primary" size="large" className="productSceneGenerate" icon={<PictureOutlined />} loading={busy} disabled={!source || !prompt.trim()} onClick={() => void generate()}>生成商品场景图</Button>
        {error && <Alert type="error" showIcon message={error} />}
      </section>
      <section className="productSceneCard" aria-label="Agent 生成的图片">
        <div className="productSceneCardHeading"><span className="productSceneStep result">02</span><div><strong>Agent 生成结果</strong><small>预览生成的场景图并下载</small></div></div>
        <div className={"productSceneOutput " + (generatedUrl ? "hasImage" : "")}>
          {busy ? <div className="productSceneEmpty"><Spin size="large" /><strong>Agent 正在创作场景图…</strong><span>图片生成可能需要约 1–3 分钟，请保持页面打开</span></div> : generatedUrl ? <img src={generatedUrl} alt="Agent 生成的商品场景图" /> : <div className="productSceneEmpty"><PictureOutlined /><strong>生成的场景图将在这里展示</strong><span>左侧上传商品图并描述场景，即可开始</span></div>}
        </div>
        <div className="productSceneOutputFooter"><Text type="secondary">{result ? "由 " + result.model + " 生成 · 已保存至文件中心" : "等待开始创作"}</Text>{result && <Button icon={<DownloadOutlined />} onClick={() => void download()}>下载图片</Button>}</div>
        <div className="productSceneTip"><ArrowRightOutlined /> 也可以进入 AI 对话，上传商品图并说“生成场景图：你的场景描述”。</div>
      </section>
    </div>
  </div>;
}
