"""启动 Open Notebook 服务器"""

import uvicorn
from app.config import load_config


def main():
    config = load_config()
    print(f"Open Notebook 启动中... http://{config.server_host}:{config.server_port}")
    uvicorn.run(
        "app.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
