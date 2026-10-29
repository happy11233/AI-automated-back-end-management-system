import { Component, Suspense, type ReactNode } from "react";

type Props = { children: ReactNode; resetKey?: string };

export function LoadingView() {
  return (
    <div className="asyncViewStatus" role="status" aria-live="polite">
      正在加载页面…
    </div>
  );
}

class ChunkErrorBoundary extends Component<Props, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidUpdate(previous: Props) {
    if (previous.resetKey !== this.props.resetKey && this.state.failed) {
      this.setState({ failed: false });
    }
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="asyncViewStatus" role="alert">
          <p>页面加载失败，请刷新后重试。</p>
          <button className="asyncViewReload" type="button" onClick={() => window.location.reload()}>
            刷新页面
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export function AsyncBoundary({ children, resetKey }: Props) {
  return (
    <ChunkErrorBoundary resetKey={resetKey}>
      <Suspense fallback={<LoadingView />}>{children}</Suspense>
    </ChunkErrorBoundary>
  );
}
