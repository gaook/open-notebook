"""启动服务器（无 reload，用于 preview）"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import uvicorn
port = int(os.environ.get("PORT", "8000"))
uvicorn.run("app.main:app", host="127.0.0.1", port=port)
