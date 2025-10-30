"""
港股分析Web管理系统
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path

# 导入路由
from .routes import upload, tasks, data, stats, filter_config

# 创建FastAPI应用
app = FastAPI(
    title="港股公告分析管理系统",
    description="基于Web界面的港股公告PDF处理和数据管理系统",
    version="1.0.0"
)

# 静态文件目录
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Jinja2模板
templates = Jinja2Templates(directory=str(templates_dir))

# 注册路由
app.include_router(upload.router)
app.include_router(tasks.router)
app.include_router(data.router)
app.include_router(stats.router)
app.include_router(filter_config.router)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """文件上传页"""
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    """任务管理页"""
    return templates.TemplateResponse("tasks.html", {"request": request})

@app.get("/data", response_class=HTMLResponse)
async def data_page(request: Request):
    """数据管理页"""
    return templates.TemplateResponse("data.html", {"request": request})

@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """统计信息页"""
    return templates.TemplateResponse("stats.html", {"request": request})

@app.get("/filter-config", response_class=HTMLResponse)
async def filter_config_page(request: Request):
    """过滤规则配置页"""
    return templates.TemplateResponse("filter_config.html", {"request": request})

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "hkex-analysis-web",
        "version": "1.0.0"
    }
