<div align="center">

# ![a5d1a4a5db0694af6d2b6385d2057504.png](https://i.miji.bid/2025/03/12/a5d1a4a5db0694af6d2b6385d2057504.png) ArxivAgent


一个基于Python的论文分析工具，可以自动获取、分析和推送arXiv上的最新论文。使用Qwen-Plus以及deepseek-r1模型来分析论文内容，生成中文摘要，并根据用户兴趣进行智能推荐与每日推送。

[![Github Stars](https://img.shields.io/github/stars/Raven-EM11/arxivagent?style=flat-square)](https://github.com/Raven-EM11/arxivagent)
[![License](https://img.shields.io/github/license/Raven-EM11/arxivagent?style=flat-square)](https://github.com/Raven-EM11/arxivagent/blob/main/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)](https://www.python.org/)

</div>

也可以直接访问网站无需部署代码[arXivAgent](http://www.arxiv.club)

## 🌟 主要特性

- 🔄 **自动获取** - 定时获取arXiv指定类别的最新论文
- 🤖 **智能分析** - 使用大语言模型进行论文内容分析
- 🔍 **智能检索** - 支持自然语言检索相关论文
- 📊 **分析报告** - 生成论文分析报告（PDF/图片格式）
- 📧 **定时推送** - 支持邮件定时推送最新论文
- 🌐 **向量检索** - 支持向量数据库存储和相似度检索

## 🚀 快速开始

### 环境要求

- Python 3.10+
- MySQL 8.0+
- wkhtmltopdf 0.12.6 (with patched qt)（用于PDF生成）

### 安装步骤

1. **创建环境**
```bash
conda create -n arxiv python=3.10
conda activate arxiv
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **安装wkhtmltopdf**

Windows:
- 从[官方网站](https://wkhtmltopdf.org/downloads.html)下载安装

Ubuntu:
```bash
# 下载带有patched qt的版本
wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.focal_amd64.deb
如果你的 Ubuntu 版本不是 focal (20.04)，可以根据你的版本选择对应的包：
Jammy (22.04): wkhtmltox_0.12.6.1-2.jammy_amd64.deb
Bionic (18.04): wkhtmltox_0.12.6-1.bionic_amd64.de

# 安装依赖
sudo apt-get install -y xfonts-75dpi xfonts-base

# 安装wkhtmltopdf
sudo dpkg -i wkhtmltox_0.12.6-1.focal_amd64.deb
sudo apt-get install -f
```

MacOS:
```bash
brew install wkhtmltopdf
```

### 4. 数据库配置

1. 创建 MySQL 数据库：

```sql
CREATE DATABASE IF NOT EXISTS arxiv 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE arxiv;

-- 创建文章表
CREATE TABLE arxiv_daily (
    entry_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    CN_title TEXT,
    authors JSON NOT NULL,
    categories JSON NOT NULL,
    primary_category VARCHAR(255),
    summary TEXT NOT NULL,
    CN_summary TEXT,
    published DATETIME NOT NULL,
    updated DATETIME,
    doi VARCHAR(255),
    journal_ref TEXT,
    comment TEXT,
    
    INDEX idx_published (published),
    INDEX idx_primary_category (primary_category),
    FULLTEXT idx_ft_title (title) WITH PARSER ngram,
    FULLTEXT idx_ft_summary (summary) WITH PARSER ngram,
    FULLTEXT idx_ft_cn (CN_title, CN_summary) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```
### 5. 安装pdf解析相关工具
运行代码进行pdf解析还需要一个en_core_web_smspacy的模型进，你可以运行如下代码来下载它
```bash
python -m spacy download en_core_web_sm
```

### 6. 配置向量数据库
可以在本地创建向量数据库文件，也可以使用zilliz官网创建自己的向量数据库，然后修改配置文件。
使用zilliz可参考文档：https://zilliz.com/docs/v2.0/zh-CN/quick-start/quick-start-python

### 7. 配置文件

复制 `config.ini.example` 为 `config.ini` 并修改相关配置：

```ini
[query]
query="希望每天检索推荐的论文主题"
category=检索论文的类别例如cs.AI,cs.CL等

[database]
user=your_db_user
password=your_db_password
host=localhost
database=arxiv
port=3306

[vectordb]
可以在zilliz官网创建自己的向量数据库，然后修改配置文件
uri=your_milvus_uri
user=your_milvus_user
password=your_milvus_password

[aliyun]
使用阿里云百炼的api，需要先在阿里云控制台创建
api_key=your_api_key

[email]
smtp_server=smtp.your_email_server.com
smtp_port=25
sender_email=your_sender_email
sender_password=your_email_password
user_email=your_recipient_email

[grobid]
# GROBID服务器地址（填写多个可以均衡负载），用于高质量地读取PDF文档
# 获取方法：复制以下空间https://huggingface.co/spaces/qingxu98/grobid，设为public，然后GROBID_URL = "https://(你的hf用户名如qingxu98)-(你的填写的空间名如grobid).hf.space"
urls=["自行创建"]
```

### 8. 运行

```bash
# 启动自动获取论文服务
python auto_arxiv_fetch.py

# 启动本地分析存储服务
python main_local.py
```

## 📃使用说明

### 1. 论文获取

默认每小时自动获取最新论文，可在 `config.ini` 中配置：

```ini
[settings]
max_results=500
arxiv_table=arxiv_daily
categories=cs.AI, cs.CR, cs.LG

[schedule]
frequency_hours=1
```

### 2. 论文分析

系统会自动分析论文并生成报告，包含：

- 中文标题和摘要
- 创新点分析
- 相关性评分
- 推荐指数

### 3. 自定义检索

可以在配置文件中通过自然语言描述配置检索需求：

```ini
[query]
query="检索文章的需求"
category=检索论文的类别例如cs.AI,cs.CL等
```

## 📁 项目结构

```
ArxivAgent/
├── auto_arxiv_fetch.py    # 自动获取论文服务
├── main_local.py         # 本地分析存储服务主程序
├── articles_processor   # 论文处理
├── models               # 数据模型
├── search_engine        # 搜索引擎
├── utils                # 工具函数
│   └── logger.py       # 日志工具
├── templates/          # 报告模板
├── scipdf/            # PDF解析工具
├── config.ini         # 配置文件
├── requirements.txt   # 项目依赖
└── README.md         # 项目文档
```

## ❓常见问题

1. PDF生成失败
   - 检查 wkhtmltopdf 是否正确安装
   - 确认文件路径权限

2. 数据库连接错误
   - 检查数据库配置信息
   - 确认数据库服务是否运行

3. API 调用失败
   - 检查 API key 配置
   - 确认网络连接

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 致谢

- [arXiv](https://arxiv.org/) - 论文数据来源
- [OpenAI](https://openai.com/) - 提供 AI 模型支持
- [Milvus](https://milvus.io/) - 向量数据库支持
- [GROBID](https://grobid.readthedocs.io/en/latest/) - 论文pdf解析工具
- [GPT Academic](https://github.com/binary-husky/gpt_academic) - 参考了其grobid url配置方案
- [ArxivDay](https://github.com/SeanMWX/ArxivDay) - 灵感来源