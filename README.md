# 🏊 消防潜水教学平台

> 面向消防系统的专业潜水在线教学平台

[![License](https://img.shields.io/badge/license-Internal-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-20.10+-blue.svg)](https://www.docker.com/)

## 📋 项目概述

消防潜水教学平台是一个完整的在线教学系统，专为消防系统消防员设计。平台严格遵循 CDSA 五级潜水认证体系，融合 NAUI、PADI、CMAS 等国际主流潜水体系的优势内容。

### 核心特点

- 🎓 **完整的 CDSA 五级体系** - 从一星到五星，共 80 节课时
- 🎬 **全动画教学** - 使用 Manim 生成分步教学动画，每一个潜水技巧一个动画视频，主角为卡通版消防员
- 📝 **交互式学习** - 练习、考试、错题本等完整功能
- 👨‍🏫 **教练端管理** - 学员管理、成绩统计、题库管理
- 🐳 **容器化部署** - Docker + Nginx，一键部署
- 🔒 **版权合规** - 不使用任何潜水组织商标，不签发证书
- ⚡ **高性能** - Redis 缓存、性能监控、API 优化
- 🧪 **完整测试** - 单元测试、集成测试、性能测试

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- Node.js 18+ (本地开发)
- Python 3.10+ (本地开发)

### 一键部署

```bash
cd /Users/wjjmac/QCLAW项目/综合潜水教学在线系统/
./deploy.sh
```

### 本地开发

**后端**:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**前端**:
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

## 📚 课程体系

### 一级潜水员 (基础入门级)
- 潜水基础理论
- 潜水装备学
- 水面与水下基础技能
- 浅水应急处置

### 二级潜水员 (应急救援潜水基础)
- 应急救援潜水概论
- 应急救援潜水装备
- 应急救援潜水技术
- 应急救援潜水安全管理

### 三级潜水员 (工程潜水基础 - 非爆破类)
- 工程潜水概论
- 水下切割技术
- 水下打捞技术
- 工程潜水管理

### 四级潜水员 (深潜与混合气体潜水)
- 深潜理论
- 声纳系统
- 减压理论
- ROV系统

### 五级潜水员 (潜水指挥与现场管理)
- 现场团队实操模拟
- 作业团队协作调度
- 应急指挥
- 横向救援技能发展

## 🏗️ 技术架构

### 后端 (FastAPI)
- RESTful API
- JWT 认证
- PostgreSQL 数据库
- Redis 缓存
- Alembic 数据库迁移

### 前端 (Next.js)
- React 18
- Ant Design UI
- TypeScript
- Zustand 状态管理

### 部署 (Docker)
- Docker Compose
- Nginx 反向代理
- PostgreSQL 容器
- Redis 容器

## 📊 项目统计

| 指标 | 数量 |
|------|------|
| 代码文件 | 76+ |
| 后端 API | 8 个 |
| 前端页面 | 20 个 |
| 课程等级 | 5 个 |
| 课时总数 | 80 节 |
| 测试文件 | 4 个 |
| 文档 | 4 个 |

## 📖 文档

- [快速开始](docs/QUICKSTART.md) - 快速开始指南
- [项目总结](docs/PROJECT_SUMMARY.md) - 项目详细说明
- [部署指南](docs/DEPLOYMENT.md) - 生产环境部署
- [贡献指南](docs/CONTRIBUTING.md) - 开发贡献规范

## 🔐 默认账号

| 角色 | 手机 | 密码 |
|------|------|------|
| 教练 | 13800138000 | admin123 |
| 学员 | 13800138001 | user123 |

## 🌐 访问地址

- 前端: `http://localhost:3000`
- 后端 API: `http://localhost:8000`
- API 文档: `http://localhost:8000/docs`

## 📁 项目结构

```
diving-platform/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/         # 8个API模块
│   │   ├── models/      # 4个数据模型
│   │   ├── crud/        # 4个CRUD操作
│   │   ├── core/        # 12个核心模块
│   │   └── main.py
│   ├── tests/           # 4个测试文件
│   ├── alembic/         # 数据库迁移
│   └── requirements.txt
├── frontend/            # Next.js 前端
│   ├── src/
│   │   ├── app/        # 20个页面
│   │   ├── components/ # 4个组件
│   │   ├── lib/        # API库
│   │   └── types/      # 类型定义
│   └── package.json
├── docker/              # Docker 配置
├── nginx/               # Nginx 配置
├── scripts/             # 脚本
│   ├── database/       # 数据库初始化
│   └── animation/      # Manim 动画
├── docs/                # 文档
└── deploy.sh            # 一键部署脚本
```

## 🧪 测试

```bash
# 后端测试
cd backend
pytest tests/

# 前端测试
cd frontend
npm run test
```

## 🔧 常用命令

```bash
# 启动服务
docker-compose -f docker/docker-compose.yml up -d

# 查看日志
docker-compose -f docker/docker-compose.yml logs -f

# 停止服务
docker-compose -f docker/docker-compose.yml down

# 初始化数据库
python scripts/database/init_all.py

# 生成动画
cd scripts/animation
./generate_animations.sh
```

## 📝 许可证

内部使用，版权所有。

## 👥 作者

由持有 PADI、CMAS、NAUI、CDSA 多体系资质的潜水教练创建。

## 📞 支持

遇到问题？
- 查看文档：`docs/`
- 查看日志：`docker-compose logs -f`
- 检查配置：`docker-compose config`

---

**项目创建时间**: 2026-03-31  
**最后更新**: 2026-03-31 08:20 GMT+8  
**开发状态**: MVP 完成，可部署 ✅