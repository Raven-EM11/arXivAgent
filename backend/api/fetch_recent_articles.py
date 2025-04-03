from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import os
import sys
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import traceback  # 添加 traceback
from utils.logger import Logger  # 导入 Logger
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, root_dir)
from models import Database, Config, LLMModel, Article
router = APIRouter()

logger = Logger.get_logger('fetch_recent_articles')  # 创建 logger

config = Config()
email_config = config.email_config()
db = Database(config.db_config())

class PaperResponse(BaseModel):
    title: str
    abstract: str
    category: str
    publishedAt: datetime
    entry_id: str
    class Config:
        from_attributes = True

@router.get("/papers", response_model=List[PaperResponse])
async def get_latest_papers(
    category: str = Query(default="all", description="Paper category")
):
    """
    获取最新的10篇论文
    使用 search_engine.py 中的 fetch_articles_from_db 方法
    """
    try:
        logger.info(f"Fetching papers for category: {category}")
        
        # 使用 SearchProcessor 的 fetch_articles_from_db 方法获取文章
        articles = db.fetch_articles_from_db_without_time(category, limit=10)
        logger.info(f"Found {len(articles)} articles")
        
        # 转换为响应格式
        response_papers = []
        for article in articles:
            try:
                paper_dict = {
                    "title": article.title,
                    "abstract": article.summary,
                    "category": article.primary_category,
                    "publishedAt": article.published,
                    "entry_id": article.entry_id
                }
                response_papers.append(paper_dict)
            except Exception as e:
                logger.error(f"Error processing article: {str(e)}")
                logger.error(traceback.format_exc())
        
        return response_papers

    except Exception as e:
        logger.error(f"Failed to fetch papers: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch papers: {str(e)}"
        )

@router.post("/papers/{entry_id}/translate", response_model=PaperResponse)
async def translate_paper(entry_id: str):
    """
    翻译指定文章的标题和摘要
    """
    try:
        logger.info(f"Translating paper with ID: {entry_id}")
        
        # 重组完整的 entry_id URL
        full_entry_id = f"http://arxiv.org/abs/{entry_id}"
        
        # 从数据库获取文章
        query = """
        SELECT entry_id, title, summary, authors, categories, 
            primary_category, published, updated, doi, 
            journal_ref, comment, full_text,
            CN_title, CN_summary
        FROM arxiv_daily
        WHERE entry_id = %s
        """
        
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, (full_entry_id,))
        row = cursor.fetchone()
        
        if not row:
            logger.error(f"Paper not found: {entry_id}")
            raise HTTPException(status_code=404, detail="Paper not found")
            
        # 创建Article对象
        article = Article(
            entry_id=row['entry_id'],
            title=row['title'],
            summary=row['summary'],
            authors=json.loads(row['authors']) if row['authors'] else [],
            categories=json.loads(row['categories']) if row['categories'] else [],
            primary_category=row['primary_category'],
            published=row['published'],
            CN_title=row['CN_title'],
            CN_summary=row['CN_summary']
        )
        
        # 如果还没有翻译，进行翻译
        if not article.CN_title or not article.CN_summary:
            llm_model = LLMModel()
            success = article.translate_content(llm_model)
            
            if success:
                # 更新数据库
                update_query = """
                UPDATE arxiv_daily 
                SET CN_title = %s, CN_summary = %s
                WHERE entry_id = %s
                """
                cursor.execute(update_query, (article.CN_title, article.CN_summary, full_entry_id))
                conn.commit()
            else:
                raise HTTPException(status_code=500, detail="Translation failed")
        
        # 返回更新后的文章信息
        return {
            "title": article.CN_title or article.title,
            "abstract": article.CN_summary or article.summary,
            "category": article.primary_category,
            "publishedAt": article.published,
            "entry_id": article.entry_id
        }
        
    except Exception as e:
        logger.error(f"Failed to translate paper: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to translate paper: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


