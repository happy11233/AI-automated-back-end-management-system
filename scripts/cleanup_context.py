from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db import close_pool, open_pool
from app.services.context_service import cleanup_expired_context


def main() -> None:
    open_pool()
    result = cleanup_expired_context()
    close_pool()
    print("上下文清理完成")
    print(result)


if __name__ == "__main__":
    main()
