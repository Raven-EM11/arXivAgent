# ArxivAgent - 智能论文助手

ArxivAgent 是一个基于 Python 的论文分析工具，可以自动获取、分析和推送 arXiv 上的最新论文。它使用qwen以及deepsee模型来分析论文内容，生成中文摘要，并根据用户兴趣进行智能推荐与每日推送。

## 主要特性

- 🔄 自动获取 arXiv 指定类别的最新论文
- 🤖 使用大语言模型进行论文内容分析
- 🔍 支持自然语言检索相关论文
- 📊 生成论文分析报告（PDF/图片格式）
- 📧 支持邮件定时推送也可以保存到本地
- 🌐 支持向量数据库存储和相似度检索
- 🈶 支持中英文双语展示

## 快速开始

### 1. 环境要求

- Python 3.8+
- MySQL 8.0+
- wkhtmltopdf（用于PDF生成）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装 wkhtmltopdf

- Windows: 从[官方网站](https://wkhtmltopdf.org/downloads.html)下载安装
- Linux: `sudo apt-get install wkhtmltopdf`
- MacOS: `brew install wkhtmltopdf`

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

### 5. 配置文件

复制 `config.ini.example` 为 `config.ini` 并修改相关配置：

```ini:README copy.md
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
使用grobid的api，需要先在grobid官网创建
urls=[""]
```

### 6. 运行

```bash
# 启动自动获取论文服务
python auto_arxiv_fetch.py

# 启动本地分析服务
python main_local.py
```

## 使用说明

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

可以通过自然语言描述检索需求：

```python
from main_local import ArxivAnalyzer

analyzer = ArxivAnalyzer()
analyzer.process_query(
    query="大模型Agent相关论文",
    category="cs.AI",
    send_to_email=True
)
```

## 项目结构

```
.
├── articles_processor.py   # 论文处理模块
├── auto_arxiv_fetch.py    # 自动获取论文
├── config.ini            # 配置文件
├── main_local.py        # 主程序
├── models.py            # 数据模型
├── search_engine.py     # 搜索引擎
├── template/            # 报告模板
└── utils/              # 工具函数
```

## 常见问题

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

## 开源协议

本项目采用 MIT 协议开源。

## 致谢

- [arXiv](https://arxiv.org/) - 论文数据来源
- [OpenAI](https://openai.com/) - 提供 AI 模型支持
- [Milvus](https://milvus.io/) - 向量数据库支持