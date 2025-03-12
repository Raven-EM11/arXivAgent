import mysql.connector
from mysql.connector import Error
import configparser
from openai import OpenAI
import json
import scipdf
import time
from typing import Dict, Any
import re
import pytz
from datetime import datetime, timedelta, timezone
import random
import requests
from functools import lru_cache
from utils.logger import Logger

logger = Logger.get_logger('models')

class LLMModel:
    """
    封装与ChatGPT模型交互的方法，主要用于将英文标题和摘要翻译成中文。
    """
    # GPT API pricing: https://openai.com/pricing
    # 换成智谱的模型
    def __init__(self, model="qwen-plus-latest"):
        self.config = Config()
        self.api_key = self.config.api_key()
        self.client = OpenAI(api_key=self.api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = model

    def prompt(self, message, temperature=0.3, max_tokens=8192, max_retries=3, retry_delay=30):
        """发送提示到LLM并获取响应"""
        for attempt in range(max_retries):
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": message,
                        }
                    ],
                    model=self.model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return chat_completion.choices[0].message.content
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.error(f"第 {attempt + 1} 次调用失败: {e}")
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"达到最大重试次数 ({max_retries})，调用最终失败: {e}")
                    raise


class Article:
    """表示从arXiv获取的文章的类，包含文章的各种元数据以及分析方法"""
    def __init__(self, authors=None, categories=None, comment=None, doi=None, entry_id=None, 
                 journal_ref=None, primary_category=None, published=None, summary=None, 
                 title=None, updated=None, CN_title=None, CN_summary=None, full_text=None):
        self.authors = authors or []
        self.categories = categories or ""
        self.comment = comment or ""
        self.doi = doi or ""
        self.entry_id = entry_id or ""
        self.journal_ref = journal_ref or ""
        self.primary_category = primary_category or ""
        self.published = published or ""
        self.summary = summary or ""
        self.title = title or ""
        self.updated = updated or ""
        self.full_text = full_text
        self.CN_title = CN_title
        self.CN_summary = CN_summary
        self._parsed_content = None

    def gpt_CN_translate(self, model):
        print("Running LLM翻译...")
        
        max_retries = 3  # 设置最大重试次数
        retries = 0

        # 翻译标题
        while retries < max_retries:
            try:
                self.CN_title = model.prompt('请帮我翻译这个文献标题：%s，只需要翻译标题，不要做任何多余回答！' % (self.title))
                if self.CN_title is None:
                    raise Exception("CN_Title 未正确翻译。")
                break
            except Exception as e:
                retries += 1
                print(f"An error occurred: {e}, Retrying... ({retries}/{max_retries})")

        # 检查是否超出重试次数
        if retries == max_retries:
            print(f"Failed to translate the TITLE of \"{self.title}\" after maximum retries.")
            return False

        # 重置重试次数
        retries = 0

        while retries < max_retries:
            try:
                self.CN_summary = model.prompt('请帮我翻译这个文献摘要：%s，只需要翻译摘要，不要做任何多余回答！' % (self.summary))
                if self.CN_summary is None:
                    raise Exception("CN_summary 未正确翻译。")
                break
            except Exception as e:
                retries += 1
                print(f"An error occurred: {e}, Retrying... ({retries}/{max_retries})")

        # 检查是否超出重试次数
        if retries == max_retries:
            print(f"Failed to translate the SUMMARY of \"{self.title}\" after maximum retries.")
            return False
            
        print("Job done.")
        return True


    def translate_content(self, model):
        """统一处理翻译的方法"""
        if not self.CN_title or not self.CN_summary:
            return self.gpt_CN_translate(model)
        return True

    @property
    def pdf_url(self) -> str:
        """获取PDF URL"""
        return self.entry_id.replace('abs', 'pdf')
    
    def get_avail_grobid_url(self):
        config = Config()
        grobid_urls = json.loads(config.grobid_urls())
        if len(grobid_urls) == 0: return None
        try:
            _grobid_url = random.choice(grobid_urls) # 随机负载均衡
            logger.info(f"使用GROBID服务: {_grobid_url}")
            if _grobid_url.endswith('/'): _grobid_url = _grobid_url.rstrip('/')
            res = requests.get(_grobid_url+'/api/isalive')
            if res.text=='true': return _grobid_url
            else: return None
        except:
            return None
    
    @lru_cache(maxsize=32)
    def _parse_pdf_content(self) -> str:
        """解析PDF全文内容，带重试机制"""
        
        grobid_url = self.get_avail_grobid_url()
        if grobid_url.endswith('/'): grobid_url = grobid_url.rstrip('/')

        if self._parsed_content is None:
            max_retries = 3  # 最大重试次数
            retry_delay = 5  # 重试间隔（秒）
            
            for attempt in range(max_retries):
                try:
                    article_dict = scipdf.parse_pdf_to_dict(self.pdf_url, as_list=False, grobid_url=grobid_url)
                    self._parsed_content = '\n\n'.join(
                        f"## {section['heading']}\n{section['text']}"
                        for section in article_dict['sections']
                    )
                    return self._parsed_content
                    
                except Exception as e:
                    if attempt < max_retries - 1:  # 如果不是最后一次尝试
                        print(f"PDF解析失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        time.sleep(retry_delay)  # 等待一段时间后重试
                    else:
                        print(f"PDF解析最终失败: {e}")
                        print("GROBID服务不可用，请修改config中的grobid urls配置，或本地部署GROBID服务")
                        # 解析失败时返回摘要作为备用内容
                        self._parsed_content = self.summary
                        
            return self._parsed_content
        return self._parsed_content

    def generate_analysis(self, query: str, model: LLMModel) -> dict:
        """生成文章分析内容"""
        llm_result = self.LLM_analysis(query, model)
        
        # 确保创新性描述是列表格式
        innovation_description = llm_result["rating"]["details"]["innovation"]
        if isinstance(innovation_description, str):
            # 如果是字符串，按行分割并清理空行
            innovation_points = [point.strip() for point in innovation_description.split('\n') if point.strip()]
        else:
            # 如果已经是列表，直接使用
            innovation_points = innovation_description
        
        return {
            "article_summary": llm_result["summary"],
            "rating_score": float(llm_result["rating"]["overall"]),
            "rating_details": {
                "创新性": {
                    "score": float(llm_result["rating"]["scores"]["innovation"]),
                    "description": innovation_points  # 使用处理后的列表
                },
                "写作质量": {
                    "score": float(llm_result["rating"]["scores"]["writing"]),
                    "description": llm_result["rating"]["details"]["writing"]
                },
                "相关程度": {
                    "score": float(llm_result["rating"]["scores"]["relevance"]),
                    "description": llm_result["rating"]["details"]["relevance"]
                }
            }
        }
    
    def LLM_analysis(self, query: str, model: LLMModel) -> str:
        """使用LLM进行分析"""
        prompt = f"""
# 角色
你是一位资深专业的论文评审专家，擅长以精准、专业且全面的视角分析各类论文。你能够运用丰富的专业知识和敏锐的洞察力，按照特定要求深入剖析文章内容。

## 技能
### 技能 1: 总结文章内容
1. 仔细研读文章，一段话总结文章内容，需全面涵盖：（1）研究背景（即作者的研究意图）、（2）采用的方法或方案、（3）设计用于证明方法的实验、（4）最终得出的结论。注意DONT SOUND LIKE AI！

### 技能 2: 分析相关性
1. 深入分析文章的研究内容与用户查询请求之间的关联度，并用一句话清晰总结。
注意：先指出相关性程度，再提供理由。内容是输出给用户的，不要输出类似"与用户提出的xxx主题契合"等说法。

### 技能 3: 提炼创新点
1. 根据文章具体内容，简略分点列出文章的创新点。
2. 将创新点与现有工作进行对比，指出相比现有工作的改进之处。

### 技能 4: 给出推荐指数
1. 从（1）方法创新性、（2）论文写作清晰程度、（3）与用户查询的相关程度这三个维度，对论文给出1 - 5分的整体推荐阅读指数。
2. 针对给出的推荐指数，一句话阐述打分理由。
3. 打分需要严格、严谨、科学。打分精确到小数点后一位
4. 注意相关性的打分理由中，不要输出类似"与用户提出的xxx主题契合"等说法。


## 输出要求
请以JSON格式输出分析结果，格式如下：
{{
    "summary": str, 使用[技能 1]总结文章内容：仔细研读文章，一段话总结文章内容，需全面涵盖：（1）研究背景（即作者的研究意图）、（2）采用的方法或方案、（3）设计用于证明方法的实验、（4）最终得出的结论。注意DONT SOUND LIKE AI！,
    "rating": {{
        "overall": "推荐指数分数"，综合创新性、写作质量、与用户查询的相关性给出推荐指数分数
        "details": {{
            "innovation": list[str], "具体打分理由： 根据[技能 3]总结创新点, 分点列出创新点及与现有工作相比的改进，需要具有一定的批判性，客观严谨",
            "writing": "str, 具体打分理由：根据文章的写作内容与写作质量给出打分，需要具有一定批判性，客观严谨",
            "relevance": "str, 具体的打分理由： 根据[技能 2]总结相关性",
        }},
        "scores": {{
            "innovation": "具体分数",
            "writing": "具体分数",
            "relevance": "具体分数"
        }}
    }},
}}

# 用户查询请求
{query}
# 文章信息
## 文章标题
{self.title}
## 文章摘要
{self.summary}
## 文章正文
{self._parse_pdf_content()}

#输出语言要求：
中文
"""     
        response = self._safe_model_call(prompt, model)
        # print(response)

        def parse_markdown_json(md_content: str) -> Dict[str, Any]:
            """
            从Markdown内容中提取并解析JSON数据
            
            :param md_content: 包含```json代码块的Markdown文本或直接的JSON文本
            :return: 解析后的Python字典
            """
            # 首先尝试使用正则表达式匹配json代码块
            pattern = r'```(?:json)?(.*?)```'
            matches = re.search(pattern, md_content, re.DOTALL)
            
            try:
                if matches:
                    # 如果找到代码块，使用代码块内容
                    json_str = matches.group(1).strip()
                else:
                    # 如果没有找到代码块，直接使用整个内容
                    json_str = md_content.strip()
                
                # 尝试解析JSON
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {str(e)}")
                print(f"尝试解析的内容: {json_str[:200]}...")  # 打印前200个字符用于调试
                raise ValueError(f"JSON解析失败: {str(e)}")
        return parse_markdown_json(response)
    
    def _safe_model_call(self, prompt: str, model: LLMModel, max_retries=3) -> str:
        """带重试机制的模型调用"""
        for _ in range(max_retries):
            try:
                response = model.prompt(prompt)
                # print(response)
                if response and len(response) > 10:  # 简单有效性检查
                    return response
            except Exception as e:
                print(f"模型调用失败: {e}")
        return "分析生成失败，请稍后再试"



class Config:
    """
    管理配置文件（config.ini）的类，用于读取数据库配置和API密钥。
    """
    def __init__(self, filename='./config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(filename)
    
    def db_config(self):
        return self.config['database']

    def query_config(self):
        return self.config['query'] 

    def email_config(self):
        return self.config['email']

    def api_key(self):
        return self.config['aliyun']['api_key']
    
    def vectordb_config(self):
        return self.config['vectordb']
    def work_time(self):
        return self.config['subscription']

    def fetch_frequency(self):
        return int(self.config['schedule']['frequency_hours'])
    
    def max_results(self):
        return int(self.config.get('settings', 'max_results', fallback='500'))
    
    def articles_table(self):
        return self.config['settings'].get('arxiv_table')
    
    def grobid_urls(self):
        return self.config['grobid'].get('urls')

    def categories(self):
        return [category.strip() for category in self.config['settings'].get('categories').split(',')]
    

class Database:
    """
    数据库操作类，用于管理与MySQL数据库的连接和操作。
    包括检查文章是否已存在于数据库中以及插入新文章。
    """
    def __init__(self, db_config):
        self.db_config = db_config

    def get_connection(self):
        return mysql.connector.connect(**self.db_config)
    
    def article_exists(self, entry_id, table_name):
        query = f"SELECT COUNT(1) FROM {table_name} WHERE entry_id = %s"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (entry_id,))
            result = cursor.fetchone()
            return result[0] > 0
    
    def fetch_articles_from_db(self, category, limit=100):
        """从数据库获取文章数据
        
        Args:
            category (str, optional): 文章类别. 默认为None表示获取所有类别
            limit (int, optional): 最大获取数量. 默认100
            
        Returns:
            list[Article]: 文章对象列表
        """
        try:
        
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            # 获取北京时间的时间范围
            beijing_tz = pytz.timezone('Asia/Shanghai')
            now = datetime.now(beijing_tz)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            
            logger.info(f"today_start: {today_start}, yesterday_start: {yesterday_start}")
            
            if category:
                query = """
                SELECT entry_id, title, summary, authors, categories, 
                    primary_category, published, updated, doi, 
                    journal_ref, comment, full_text,
                    CN_title, CN_summary
                FROM arxiv_daily
                WHERE JSON_CONTAINS(categories, %s)  -- 使用JSON_CONTAINS检查categories数组
                AND published >= %s
                AND published < %s
                ORDER BY published DESC
                LIMIT %s
                """
                cursor.execute(query, (
                    json.dumps(category),  # 将category转换为JSON字符串
                    yesterday_start,
                    today_start,
                    limit
                ))
            else:
                query = """
                SELECT entry_id, title, summary, authors, categories, 
                    primary_category, published, updated, doi, 
                    journal_ref, comment, full_text,
                    CN_title, CN_summary
                FROM arxiv_daily
                WHERE published >= %s
                AND published < %s
                ORDER BY published DESC
                LIMIT %s
                """
                cursor.execute(query, (
                    yesterday_start,
                    today_start,
                    limit
                ))
                
            rows = cursor.fetchall()
            
            articles = []
            for row in rows:
                # 将JSON字符串转换为Python对象
                authors = json.loads(row['authors']) if row['authors'] else []
                categories = json.loads(row['categories']) if row['categories'] else []
               
                
                # 将UTC时间转换回北京时间
                published = row['published'].astimezone(beijing_tz) if row['published'] else None
                updated = row['updated'].astimezone(beijing_tz) if row['updated'] else None
                
                article = Article(
                    authors=authors,
                    categories=categories,
                    comment=row['comment'],
                    doi=row['doi'],
                    entry_id=row['entry_id'],
                    journal_ref=row['journal_ref'],
                    primary_category=row['primary_category'],
                    published=published,
                    summary=row['summary'],
                    title=row['title'],
                    updated=updated,
                    CN_title=row['CN_title'],
                    CN_summary=row['CN_summary'],
                    full_text=row['full_text']
                )
                articles.append(article)
                
            return articles
            
        except Error as e:
            print(f"数据库错误: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()  
                conn.close()
    
    def fetch_articles_from_db_without_time(self, category, limit=100):
        """从数据库获取文章数据
        
        Args:
            category (str): 文章主分类
            limit (int, optional): 最大获取数量. 默认10
            
        Returns:
            list[Article]: 文章对象列表
        """
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        
        if category:
            query = """
            SELECT entry_id, title, summary, authors, categories, 
                primary_category, published, updated, doi, 
                journal_ref, comment, full_text,
                CN_title, CN_summary
            FROM arxiv_daily
            WHERE primary_category = %s
            ORDER BY published DESC
            LIMIT %s
            """
            cursor.execute(query, (
                category,  # 直接使用category字符串，不需要json.dumps
                limit
            ))
        else:
            query = """
            SELECT entry_id, title, summary, authors, categories, 
                primary_category, published, updated, doi, 
                journal_ref, comment, full_text,
                CN_title, CN_summary
            FROM arxiv_daily
            ORDER BY published DESC
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            
        rows = cursor.fetchall()
        
        articles = []
        for row in rows:
            # 将JSON字符串转换为Python对象
            authors = json.loads(row['authors']) if row['authors'] else []
            categories = json.loads(row['categories']) if row['categories'] else []
            
            article = Article(
                authors=authors,
                categories=categories,
                comment=row['comment'],
                doi=row['doi'],
                entry_id=row['entry_id'],
                journal_ref=row['journal_ref'],
                primary_category=row['primary_category'],
                published=row['published'],
                summary=row['summary'],
                title=row['title'],
                updated=row['updated'],
                CN_title=row['CN_title'],
                CN_summary=row['CN_summary'],
                full_text=row['full_text']
            )
            articles.append(article)
            
        return articles
