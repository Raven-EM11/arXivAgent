import json
import os
import pickle
from openai import OpenAI
from pymilvus import MilvusClient, DataType
from cozepy import Coze, TokenAuth, COZE_CN_BASE_URL, Message, ChatEventType
from dotenv import load_dotenv, find_dotenv
from models import LLMModel, Database, Config
from articles_processor import ArticlePostProcessor
import pytz
from datetime import datetime, timedelta, timezone
import threading
import time
import logging

logger = logging.getLogger(__name__)

class VectorCache:
    """向量缓存管理类"""
    def __init__(self, cache_file="vector_cache.pkl"):
        self.cache_file = cache_file
        self.cache = {}
        self.load_cache()
    
    def load_cache(self):
        """从文件加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.cache = pickle.load(f)
            except Exception as e:
                print(f"加载缓存失败: {e}")
    
    def save_cache(self):
        """保存缓存到文件"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
    def get(self, text):
        """获取向量"""
        return self.cache.get(text)
    
    def set(self, text, vector):
        """设置向量"""
        self.cache[text] = vector
        self.save_cache()

class VectorDB:
    """向量数据库管理类"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """实现单例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        """初始化数据库连接"""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self._client = None
        self._lock = threading.Lock()
        
        self.config = Config()
        
        # 使用服务器模式配置
        self.uri = self.config.vectordb_config()['uri']  # Milvus 服务器地址
        self.user = self.config.vectordb_config()['user']  # 默认用户名
        self.password = self.config.vectordb_config()['password']  # 默认密码
        
        # 初始化OpenAI客户端
        self.embedding_client = OpenAI(
            api_key=self.config.api_key(),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.vector_cache = VectorCache()
        
        # 初始化连接
        self._init_connection()
        
    def _init_connection(self, max_retries=3, retry_delay=5):
        """初始化数据库连接，带重试机制"""
        for attempt in range(max_retries):
            try:
                with self._lock:
                    if self._client is None:
                        self._client = MilvusClient(
                            uri=self.uri,
                            user=self.user,
                            password=self.password
                        )
                        self.init_collection()
                        self._client.load_collection("articles")
                        logger.info("成功加载集合 'articles' 到内存")
                    return
            except Exception as e:
                logger.error(f"连接数据库失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    raise ConnectionError(f"无法连接到向量数据库: {e}")

    def _ensure_connection(self):
        """确保数据库连接可用"""
        if self._client is None:
            self._init_connection()
        return self._client

    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self._client is not None:
                try:
                    # 如果MilvusClient有close方法的话
                    self._client.close()
                except Exception as e:
                    logger.error(f"关闭数据库连接时出错: {e}")
                finally:
                    self._client = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    def init_collection(self):
        """初始化集合"""
        try:
            collection_name = "articles"
            client = self._ensure_connection()
            
            # 检查集合是否已存在
            if client.list_collections() and collection_name in client.list_collections():
                logger.info(f"集合 {collection_name} 已存在")
                return
                
            # 创建新集合
            schema = MilvusClient.create_schema(
                auto_id=True,
                enable_dynamic_field=True
            )
            
            # 定义所有需要的字段
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1024)
            schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=500)
            schema.add_field(field_name="abstract", datatype=DataType.VARCHAR, max_length=2000)
            schema.add_field(
                field_name="categories", 
                datatype=DataType.ARRAY, 
                element_type=DataType.VARCHAR,
                max_length=100,     # 数组中每个字符串的最大长度
                max_capacity=20     # 数组可以包含的最大元素数量
            )
            schema.add_field(field_name="primary_category", datatype=DataType.VARCHAR, max_length=100)
            schema.add_field(field_name="published_time", datatype=DataType.INT64)
            
            index_params = client.prepare_index_params()
            index_params.add_index(
                field_name="vector", 
                index_type="IVF_FLAT", 
                metric_type="IP", 
                params={"nlist": 128}
            )
            
            try:
                client.create_collection(
                    collection_name=collection_name,
                    schema=schema,
                    index_params=index_params
                )
                logger.info(f"成功创建集合: {collection_name}")
            except Exception as e:
                logger.error(f"创建集合失败: {e}")
                raise e
                
        except Exception as e:
            logger.error(f"初始化集合时出错: {e}")
            raise e

    def insert_article(self, article, max_retries=3):
        """插入文章到统一的collection"""
        for attempt in range(max_retries):
            try:
                client = self._ensure_connection()
                # 组合文本用于生成向量
                combined_text = f"{article.title} {article.summary}"
                vector = self.get_embedding(combined_text)
                # print(f"article.published: {article.published}")
                # 将发布时间转换为时间戳
                if isinstance(article.published, str):
                    # 如果是字符串，先转换为datetime对象（假设输入是北京时间）
                    beijing_time = datetime.fromisoformat(article.published.replace('Z', '+08:00'))
                    # 转换为UTC时间
                    utc_time = beijing_time.astimezone(timezone.utc)
                    published_timestamp = int(utc_time.timestamp())
                elif isinstance(article.published, datetime):
                    # 如果已经是datetime对象（假设是北京时间）
                    if article.published.tzinfo is None:
                        # 如果没有时区信息，假设是北京时间
                        beijing_tz = timezone(timedelta(hours=8))
                        beijing_time = article.published.replace(tzinfo=beijing_tz)
                        utc_time = beijing_time.astimezone(timezone.utc)
                    else:
                        # 如果已经有时区信息，直接转换为UTC
                        utc_time = article.published.astimezone(timezone.utc)
                    published_timestamp = int(utc_time.timestamp())
                
                # 检查文章是否已存在
                existing = client.search(
                    collection_name="articles",
                    data=[vector],
                    output_fields=["title"],
                    search_params={"metric_type": "IP", "params": {"nprobe": 10}},
                    limit=1
                )
                
                # 如果找到完全相同的文章（相似度接近1.0），跳过插入
                if existing and existing[0] and existing[0][0]["distance"] > 0.99:
                    print(f"文章已存在，跳过: {article.title}")
                    return False
                
                # 处理文章类别
                # 如果categories是字符串，先转换为列表
                if isinstance(article.categories, str):
                    categories = article.categories.split()
                else:
                    categories = article.categories
                    
                # 插入新文章
                client.insert(
                    collection_name="articles",
                    data={
                        "vector": vector,
                        "title": article.title,
                        "abstract": article.summary,
                        "categories": categories,  # 存储所有类别
                        "primary_category": article.primary_category,  # 仍然保留主要类别
                        "published_time": published_timestamp  # 添加发布时间
                    }
                )
                # print(f"成功插入文章: {article.title}")
                return True
                
            except Exception as e:
                logger.error(f"插入文章失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    self._init_connection()  # 重新初始化连接
                else:
                    return False

    def search_similar_articles(self, query, category, threshold=0.1, limit=1000, max_retries=3):
        """搜索相似文章"""
        for attempt in range(max_retries):
            try:
                client = self._ensure_connection()
                query_vector = self.get_embedding(query)
                
                # 获取北京时间的时间范围，过滤最近一天的文章从昨天0点到今天零点
                beijing_tz = pytz.timezone('Asia/Shanghai')
                now = datetime.now(beijing_tz)
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                yesterday_start = today_start - timedelta(days=3)
                
                # 转换为时间戳 
                start_timestamp = int(yesterday_start.timestamp())
                end_timestamp = int(today_start.timestamp())
                
                # 构建过滤表达式（根据官方文档修正）
                filter_expr = f'published_time >= {start_timestamp} && published_time < {end_timestamp}'
                if category:
                    # 使用ARRAY_CONTAINS操作符代替contains方法
                    filter_expr += f' && ARRAY_CONTAINS(categories, "{category}")'
                
                results = client.search(
                    collection_name="articles",
                    data=[query_vector],
                    filter=filter_expr,
                    limit=limit,
                    output_fields=["title", "abstract", "categories", "published_time"],
                )
                
                matches = []
                for hit in results[0]:
                    if hit['distance'] >= threshold:
                        # 将时间戳转换回北京时间的datetime对象
                        published_time = datetime.fromtimestamp(hit['entity']['published_time'], beijing_tz)
                        matches.append({
                            "title": hit['entity']['title'],
                            "abstract": hit['entity']['abstract'], 
                            "categories": hit['entity']['categories'],
                            "published_time": published_time.isoformat(),
                            "score": hit['distance']
                        })
                return matches
                
            except Exception as e:
                logger.error(f"搜索文章失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    self._init_connection()  # 重新初始化连接
                else:
                    return []

    def search_similar_articles_without_time(self, query, category, threshold=0.1, limit=1000):
        """根据类别和时间范围过滤文章,然后搜索相似文章"""
        collection_name = "articles"
        
        query_vector = self.get_embedding(query)
        filter_expr = f"ARRAY_CONTAINS(categories, '{category}')"
        
        try:
            results = self._ensure_connection().search(
                collection_name=collection_name,
                data=[query_vector],
                filter=filter_expr,
                limit=limit,
                output_fields=["title", "abstract", "categories", "published_time"],
            )
            
            matches = []
            # 获取北京时间的时间范围，过滤最近一天的文章从昨天0点到今天零点
            beijing_tz = pytz.timezone('Asia/Shanghai')
            for hit in results[0]:
                if hit['distance'] >= threshold:
                    # 将时间戳转换回北京时间的datetime对象
                    published_time = datetime.fromtimestamp(hit['entity']['published_time'], beijing_tz)
                    matches.append({
                        "title": hit['entity']['title'],
                        "abstract": hit['entity']['abstract'], 
                        "categories": hit['entity']['categories'],
                        "published_time": published_time.isoformat(),
                        "score": hit['distance']
                    })
            return matches
            
        except Exception as e:
            print(f"搜索相似文章时出错: {e}")
            return []

    def get_embedding(self, text):
        """获取文本的embedding向量，优先使用缓存"""
        cached_vector = self.vector_cache.get(text)
        if cached_vector is not None:
            return cached_vector
        
        try:
            completion = self.embedding_client.embeddings.create(
                model="text-embedding-v3",
                input=text,
                dimensions=1024,
                encoding_format="float"
            )
            
            vector = completion.data[0].embedding
            # 异步缓存向量
            self.vector_cache.set(text, vector)
            return vector
        except Exception as e:
            logger.error(f"生成向量失败: {e}")
            raise e

class SearchProcessor:
    """
    处理用户搜索请求的类，实现多阶段过滤
    """
    def __init__(self, db_config, llm:LLMModel=None):
        """
        初始化搜索处理器
        
        参数:
        - db_config: 数据库配置
        - llm: LLMModel实例
        """
        self.db = Database(db_config)
        self.llm = llm
        self.config = Config()
        # 将向量数据库初始化改为延迟加载
        self._vector_db = None
        
        # 初始化OpenAI客户端
        self.embedding_client = OpenAI(
            api_key=self.config.api_key(),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        ) 
    
    @property
    def vector_db(self):
        """延迟初始化向量数据库"""
        if self._vector_db is None:
            self._vector_db = VectorDB()
        return self._vector_db
    
    def insert_article_to_vector_db(self, article):
        """
        插入文章到向量数据库
        
        参数:
        - article: 包含title和abstract的字典
        
        返回:
        - bool: 插入是否成功
        """
        return self.vector_db.insert_article(article)
    
    def search_similar_articles(self, query, category, threshold=0.1, limit=50):
        """搜索相似文章"""
        return self.vector_db.search_similar_articles(query, category, threshold, limit)
    
    def search_similar_articles_without_time(self, query, category, threshold=0.1, limit=50):
        """搜索相似文章, 不添加时间条件"""
        return self.vector_db.search_similar_articles_without_time(query, category, threshold, limit)

    
    def extract_keywords_qwen(self, query):
        """
        使用千问模型提取查询中的关键词
        
        参数:
        - query: 用户的查询字符串
        
        返回:
        - keywords: 提取出的关键词列表
        """
        try:
            prompt = f"""
            # 角色
你是一位专业的关键词提取专家，擅长从各种文本中精准提取关键信息，并将中文关键词准确翻译为英文或对应的缩写。

## 技能
### 技能 1: 提取关键词
1. 仔细分析用户输入的请求内容。
2. 精准提取其中的关键词。
3. 若关键词为中文，将其翻译为英文或对应的缩写，最终以列表List[str]的格式输出。

## 限制:
- 仅返回关键词列表，不进行额外解释或说明。
- 输出格式必须严格为列表List[str] 。
- 确保英文翻译或缩写的准确性。 
- 
## 案例
- 用户输入：大模型Agent相关论文，
- 输出：["large language model", "Agent"]
注意不要输出任何额外文字
# 任务开始：
- 用户输入：{query}
- 输出：
            """
            
            response = self.llm.prompt(prompt, temperature=0.1)
            
            keywords_str = response.strip()
            try:
                return json.loads(keywords_str)
            except json.JSONDecodeError:
                print(f"无法解析关键词JSON: {keywords_str}")
                return query.split()  # 降级为简单分词
                
        except Exception as e:
            print(f"千问API调用出错: {e}")
            return query.split()  # 降级为简单分词
    
    def keyword_filter(self, query, articles):
        """第一阶段：关键词预过滤"""
        # 使用Coze API或千问API提取关键词
        # keywords = self.extract_keywords_coze(query)  # 使用Coze
        keywords = self.extract_keywords_qwen(query)    # 使用千问
        print("得到的关键词为:", keywords)
        # 关键词过滤
        filtered_articles = []
        for article in articles:
            text = f"{article.title.lower()} {article.summary.lower()}"
            if any(keyword.lower() in text for keyword in keywords):
                filtered_articles.append(article)
                
        return filtered_articles
    
    def embedding_filter(self, query, articles, category, threshold=0.5):
        """
        第二阶段：embedding相似度过滤
        
        参数:
        - query: 用户查询字符串
        - articles: 待过滤的文章列表
        - threshold: 相似度阈值
        
        返回:
        - filtered_articles: 经过embedding过滤的文章列表
        - keywords: 提取出的关键词列表
        """
        # 使用search_similar_articles获取相似文章
        # 改为针对query中的关键词进行相似度匹配
        keywords = self.extract_keywords_qwen(query)
        print(f"\n测试查询: {query}")
        print(f"\n测试查询关键词为: {keywords}")
        # similar_results = self.search_similar_articles(query, threshold=threshold)
        similar_results = self.search_similar_articles(" ".join(keywords), category, threshold=threshold)
        # similar_results = self.search_similar_articles_without_time(" ".join(keywords), category, threshold=threshold)
        # print("similar_results", similar_results)
        # 根据搜索结果过滤原文章列表
        filtered_articles = []
        similar_titles = {result['title'] for result in similar_results}  # 使用集合提高查找效率
        for article in articles:
            if article.title in similar_titles:
                filtered_articles.append(article)
                
        return filtered_articles, keywords
    
    def llm_filter(self, query, articles, keywords, batch_size=10):
        """
        第三阶段：LLM精准判断（批量处理）
        
        参数:
        - query: 用户查询字符串
        - articles: 待过滤的文章列表
        - batch_size: 批量处理大小，默认10篇
        
        返回:
        - filtered_articles: 经过LLM判断的文章列表
        """
        filtered_articles = []
        
        # 将文章列表分批处理
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            
            # 构建批量文章的文本
            articles_text = "\n\n".join([
                f"文章{j+1}:\n标题：{article.title}\n摘要：{article.summary}"
                for j, article in enumerate(batch)
            ])
            
            prompt = f"""
            # 角色
            你是一位专业且严谨的科研信息筛选专家，在各个科研领域都有深厚的知识储备，擅长精准地从大量文章中筛选出符合特定需求的内容。

            ## 任务说明
            1. 分析以下检索需求和多篇文章内容
            2. 判断每篇文章是否与检索需求相关，注意需要直接相关，即文章内容与每一个检索关键词都直接相关。
            3. 将相关文章的标题以JSON数组格式返回
            
            ## 输出要求
            - 仅返回相关文章的标题列表
            - 必须是JSON数组格式，如：["标题1", "标题2"]
            - 如果没有相关文章，返回空数组 []
            - 不要包含任何其他解释或说明文字
            
            # 开始执行任务
            检索需求：{query}
            检索关键词：{keywords}

            待分析文章：
            {articles_text}

            请返回相关文章的标题列表（JSON数组格式）：
            """
            try:
                print("LLM开始执行过滤任务")
                response = self.llm.prompt(prompt, temperature=0.1)
                # print("response: ", response)
                # 解析返回的JSON数组
                try:
                    result = response.strip()
                    relevant_titles = json.loads(result)
                    
                    # 验证返回格式
                    if not isinstance(relevant_titles, list):
                        print(f"LLM返回格式错误，应为列表而不是 {type(relevant_titles)}")
                        continue
                    
                    # 根据标题匹配找到相关文章
                    for article in batch:
                        if article.title in relevant_titles:
                            filtered_articles.append(article)
                            
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {e}")
                    print(f"原始返回内容: {result}")
                    continue
                    
            except Exception as e:
                print(f"LLM API调用错误: {e}")
                continue
            
        return filtered_articles
    
    def process_search(self, query, category, initial_articles):
        """
        处理搜索请求的主函数，按顺序执行三个过滤阶段
        
        参数:
        - query: 用户查询字符串
        - category: 文章类别
        - initial_articles: 初始文章列表
        
        返回:
        - final_articles: 最终筛选出的文章列表
        - stats: 各阶段的统计信息
        """
        stats = {
            "initial_count": len(initial_articles),
            "keyword_filter_count": 0,
            "embedding_filter_count": 0,
            "llm_filter_count": 0
        }
        
        # 第一阶段：关键词过滤
        keyword_filtered = self.keyword_filter(query, initial_articles)
        stats["keyword_filter_count"] = len(keyword_filtered)
        print(f"关键词过滤后剩余文章数: {len(keyword_filtered)}")
        
        if not keyword_filtered:
            return [], stats
            
        # 第二阶段：embedding过滤
        embedding_filtered = self.embedding_filter(query, keyword_filtered)
        stats["embedding_filter_count"] = len(embedding_filtered)
        print(f"Embedding过滤后剩余文章数: {len(embedding_filtered)}")
        
        if not embedding_filtered:
            return [], stats
            
        # 第三阶段：LLM判断
        final_articles = self.llm_filter(query, embedding_filtered)
        stats["llm_filter_count"] = len(final_articles)
        print(f"LLM判断后最终文章数: {len(final_articles)}")
        
        # 添加后处理
        post_processor = ArticlePostProcessor(self.client)
        final_reports = post_processor.process_batch(final_articles, query)
        
        return final_articles, stats, final_reports

    def fetch_articles_from_db(self, category, limit=100):
        """从数据库获取文章数据
        
        Args:
            category (str, optional): 文章类别. 默认为None表示获取所有类别
            limit (int, optional): 最大获取数量. 默认100
            
        Returns:
            list[Article]: 文章对象列表
        """
        articles = self.db.fetch_articles_from_db(category, limit)
        return articles
    
    def fetch_articles_from_db_without_time(self, category, limit=1000):
        """从数据库获取文章数据
        
        Args:
            category (str, optional): 文章类别. 默认为None表示获取所有类别
            limit (int, optional): 最大获取数量. 默认100
            
        Returns:
            list[Article]: 文章对象列表
        """
        
        articles = self.db.fetch_articles_from_db_without_time(category, limit)
            
        return articles

def create_search_processor(config):
    """
    创建SearchProcessor实例的工厂函数
    
    参数:
    - config: 配置对象
    
    返回:
    - SearchProcessor实例
    """
    api_client = OpenAI(
        api_key=config.api_key(),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    return SearchProcessor(config.db_config(), api_client)

