from datetime import datetime, timedelta, timezone
import arxiv
from mysql.connector import Error
import schedule
import time
import json  # 添加json模块导入
import sys 
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, root_dir)
from search_engine import create_search_processor
from models import Article, Config, Database, LLMModel
from utils.logger import Logger

logger = Logger.get_logger('auto_arxiv_fetch')
search_processor = create_search_processor(Config())

def fetch_recent_articles(category, max_results=2000):
    """
    获取最近更新的文章列表。通过arXiv API获取指定分类下最新的文章列表。
    使用北京时间确定范围，但转换为GMT时间进行查询。
    """
    client = arxiv.Client(
        page_size=100,
        delay_seconds=3,  # 增加请求间隔
        num_retries=5     # 增加重试次数
    )
    
    # 获取北京时间的昨天零点
    beijing_tz = timezone(timedelta(hours=8))
    today_beijing = (datetime.now(beijing_tz)-timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 转换为GMT时间
    start_date = (today_beijing.astimezone(timezone.utc)-timedelta(days=1)).strftime('%Y%m%d%H%M')
    end_date = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
    
    # 构建符合arXiv API格式的查询字符串
    query = f"{category} AND submittedDate:[{start_date} TO {end_date}]"
    logger.info(f"查询时间范围: {start_date} TO {end_date} (GMT)")
    logger.info(f"对应北京时间: {today_beijing.strftime('%Y-%m-%d %H:%M')} TO {datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M')}")

    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.LastUpdatedDate
    )

    articles_list = []
    max_attempts = 5  # 最大重试次数
    retry_delay = 10  # 重试间隔（秒）
    
    for attempt in range(max_attempts):
        try:
            for r in client.results(search):
                # 转换发布时间和更新时间为北京时间
                beijing_tz = timezone(timedelta(hours=8))
                published_beijing = r.published.astimezone(beijing_tz) if r.published else None
                updated_beijing = r.updated.astimezone(beijing_tz) if r.updated else None
                article = Article(
                    r.authors, r.categories, r.comment, r.doi,
                    r.entry_id, r.journal_ref, 
                    r.primary_category, published_beijing, r.summary, r.title, updated_beijing
                )
                articles_list.append(article)
            break
            
        except Exception as e:
            logger.error(f"获取文章时出错 (尝试 {attempt + 1}/{max_attempts}): {e}")
            if attempt < max_attempts - 1:
                logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避，每次重试增加等待时间
            else:
                logger.error("达到最大重试次数，放弃获取文章")
                return []
    
    return articles_list

def fetch_process_insert_articles(category, table_name, max_results):
    """
    处理文章列表：直接插入数据库，避免重复。集成了文章获取和插入数据库的过程，只对数据库中不存在的新文章进行处理。
    """
    config = Config()
    db = Database(config.db_config())

    logger.info(f"（{datetime.now().date()}）：开始获取{category}文章...")
    max_retries = 3  # 设置最大重试次数
    retries = 0
    # 检索文章
    while retries < max_retries:
        try:
            articles = fetch_recent_articles(category, max_results)
            break
        except Exception as e:
            retries += 1
            logger.error(f"An error occurred: {e}, Retrying... ({retries}/{max_retries})")

    # 检查是否超出重试次数
    if retries == max_retries:
        logger.error(f"无法正确从Arxiv.org获取文章。")
        return False

    new_articles = []
    if articles:
        for article in articles:
            if not db.article_exists(article.entry_id, table_name):
                new_articles.append(article)
    else:
        logger.info(f"（{datetime.now().date()}）：没有获取到任何{category}文章。")
    
    if new_articles:
        logger.info(f"准备存储{category}新文章{len(new_articles)}篇。")
        insert_articles_to_database(category, new_articles, table_name)  # 插入新文章到数据库
        logger.info(f"成功存储{len(new_articles)}篇新文章到数据库中。")
        # 将新文章插入统一的向量数据库
        for article in new_articles:
            search_processor.insert_article_to_vector_db(article)
        logger.info(f"成功存储{len(new_articles)}篇新文章到向量数据库中。")
    else:
        logger.info("没有新的文章需要更新。")

def insert_articles_to_database(category, articles, table_name):
    """
    将文章数据插入数据库。负责将处理过的文章数据批量插入数据库中。
    字段 authors, categories,  使用 JSON 格式存储。
    将UTC时间转换为北京时间。
    """
    model = LLMModel()
    insert_query = f"""
    INSERT INTO {table_name} 
    (title, summary, published, authors, categories, comment, doi, entry_id, 
    journal_ref, primary_category, updated, CN_title, CN_summary, author_affiliations) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    records = []
    
    # 对文章按发布时间排序，获取最新的10篇进行翻译
    articles_in_category = [article for article in articles if article.primary_category == category]
    articles_to_translate = sorted(
        articles_in_category, 
        key=lambda x: x.published if x.published else datetime.min,
        reverse=True
    )[:10]
    
    logger.info(f"开始翻译最新的{len(articles_to_translate)}篇文章...")
    for article in articles_to_translate:
        try:
            article.translate_content(model)
            logger.info(f"成功翻译文章：{article.title[:50]}...")
        except Exception as e:
            logger.error(f"翻译文章时出错：{str(e)}")

    for article in articles:
        # 获取每篇文章的作者与所属机构相关信息
        article.get_author_and_affiliation(model)
        logger.info(f"成功获取文章：{article.title[:50]}的作者与所属机构相关信息：{article.author_and_affiliation}")
        
    for article in articles:
        # 将Author对象列表转换为作者名字的列表，然后转换为JSON字符串
        authors_json = json.dumps([str(author) for author in article.authors])
        categories_json = json.dumps(article.categories.split(',') if isinstance(article.categories, str) else article.categories)
        author_affiliations_json = json.dumps(article.author_and_affiliation)
        
        record = (
            article.title, 
            article.summary, 
            article.published,     
            authors_json,
            categories_json,
            article.comment,
            article.doi,
            article.entry_id,
            article.journal_ref,
            article.primary_category,
            article.updated,       
            getattr(article, 'CN_title', None),    # 获取翻译后的标题，如果没有则为None
            getattr(article, 'CN_summary', None),    # 获取翻译后的摘要，如果没有则为None
            author_affiliations_json
        )
        records.append(record)

    config = Config()
    db = Database(config.db_config())

    # try:
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.executemany(insert_query, records)
    conn.commit()
    logger.info(f"{cursor.rowcount} records inserted.")
    # except Error as e:
    #     print(f"数据库插入错误: {e}")
    #     conn.rollback()
    # finally:
    #     cursor.close()
    #     conn.close()

def daily_task():
    """
    定义定时任务要执行的操作。对配置文件中指定的每个文章分类，调用`fetch_process_insert_articles`函数进行文章的抓取、处理和插入操作。
    """
    config = Config()
    for category in config.categories():
        fetch_process_insert_articles(category, config.articles_table(), config.max_results())
    

# 主程序流程
if __name__ == "__main__":
    config = Config()
    frequency_hours = config.fetch_frequency()  # 获取收录频率
    logger.info(f"当前本地时间: {datetime.now()}")
    daily_task()
    schedule.every(frequency_hours).hours.do(daily_task)

    while True:
        # 获取当前时间
        logger.info(f"当前本地时间: {datetime.now()}")
        # 运行所有可以运行的任务
        schedule.run_pending()
        time.sleep(60)  # 暂停一分钟
