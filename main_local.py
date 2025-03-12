from datetime import datetime
import os
from models import Config, LLMModel
from search_engine import SearchProcessor
from articles_processor import ArticlePostProcessor

import re
import schedule
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


class ArxivAnalyzer:
    """arXiv论文分析器主类"""
    def __init__(self):
        self.config = Config()
        self.model = LLMModel()
        self.search_processor = SearchProcessor(self.config.db_config(), self.model)
        self.post_processor = ArticlePostProcessor(self.model)
        
    def process_query(self, query: str, category: str, send_to_email: bool = False, max_results: int = 50):

        """处理用户查询并分析论文"""
        print(f"\n开始处理查询: {query}")
        print(f"类别: {category if category else '所有类别'}")
        
        # 获取最新文章
        articles = self.search_processor.fetch_articles_from_db(category, limit=max_results)
        if not articles:
            print("未获取到任何文章")
            return
            
        print(f"获取到 {len(articles)} 篇文章")
        
        # # 多阶段过滤
        # # 第一阶段：关键词过滤
        # keyword_filtered = self.search_processor.keyword_filter(query, articles)
        # print(f"\n关键词过滤后剩余: {len(keyword_filtered)} 篇文章")
        
        # if not keyword_filtered:
        #     print("未找到相关文章")
        #     return
            
        # 第一阶段：embedding过滤
        embedding_filtered, keywords = self.search_processor.embedding_filter(query, articles, category)
        print(f"\nEmbedding过滤后剩余: {len(embedding_filtered)} 篇文章")
        
        if not embedding_filtered:
            print("未找到相关文章")
            return
            
        # 第二阶段：LLM精确判断
        final_articles = self.search_processor.llm_filter(query, embedding_filtered, keywords)
        print(f"\nLLM过滤后最终剩余: {len(final_articles)} 篇文章")
        
        if not final_articles:
            print("未找到相关文章")
            return
            
        # 生成分析报告
        print("\n开始生成分析报告...")
        # 创建以当前时间命名的输出目录
        current_time = datetime.now().strftime('%Y%m%d_%H%M')
        output_dir = os.path.join(os.getcwd(), "analysis_report", current_time)
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_files = []
        for i, article in enumerate(final_articles, 1):
            print(f"\n处理第 {i} 篇文章: {article.title}")
            try:
                # 翻译文章标题和摘要内容
                article.translate_content(self.model)
                # 解析pdf内容
                article._parse_pdf_content()
                # 生成分析报告
                self.post_processor.process_article(
                    article, 
                    query,
                    template_name='v1.html',
                    output_dir=output_dir  # 传递输出目录到process_article方法
                )
                
                # 收集PDF文件路径
                # safe_id = article.entry_id.split('/')[-1].replace('.', '_')
                safe_id = re.sub(r'[^\w\-_.]', '_', article.entry_id.split('/')[-1])
                pdf_path = os.path.join(output_dir, f"report_{safe_id}.pdf")
        
                print(pdf_path)
                if os.path.exists(pdf_path):
                    pdf_files.append(pdf_path)
                    
            except Exception as e:
                print(f"处理文章时出错: {e}")
                continue
        print(pdf_files)
        # 合并所有PDF文件，保存在同一时间目录下
        if len(pdf_files) > 1:
            merged_pdf_path = os.path.join(output_dir, f"merged_report.pdf")
            self.post_processor.merge_pdfs(pdf_files, merged_pdf_path)
            print(f"\n已生成合并报告: {merged_pdf_path}")
            
            # 发送合并报告到邮箱
            if send_to_email:
                print("发送合并报告到邮箱")
                # if hasattr(self.config, 'email_config') and self.config.email_config():
                #     # 假设用户邮箱通过某种方式获取
                #     user_email = self.config.email_config().get('user_email')  
                #     self.send_report_email(merged_pdf_path, query, user_email)
            
        print(f"\n所有报告已保存到目录: {output_dir}")



    def send_report_email(self, pdf_path, query_topic, recipient_email=None):
        """将生成的PDF报告发送到用户邮箱

        Args:
            pdf_path: PDF报告的路径
            query_topic: 查询主题
            recipient_email: 收件人邮箱，如果为None则尝试从配置中获取
        """
        try:
            email_config = self.config.email_config()
            if not email_config:
                print("未找到邮箱配置，跳过邮件发送")
                return
            
            # 提取邮箱配置
            smtp_server = email_config.get('smtp_server')
            smtp_port = email_config.get('smtp_port')
            sender_email = email_config.get('sender_email')
            sender_password = email_config.get('sender_password')
        
            # 如果没有提供收件人邮箱，尝试从配置中获取
            if recipient_email is None:
                recipient_email = email_config.get('recipient_email')
        
            if not all([smtp_server, smtp_port, sender_email, sender_password, recipient_email]):
                print("邮箱配置不完整或未提供收件人邮箱，跳过邮件发送")
                return
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"arXiv论文分析报告 - {query_topic} - {datetime.now().strftime('%Y-%m-%d')}"
        
            # 邮件正文
            body = f"""您好，

    这是您订阅的arXiv论文分析报告，主题为"{query_topic}"。
    报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    此邮件由系统自动发送，请勿回复。
    """
            msg.attach(MIMEText(body, 'plain'))
        
            # 添加PDF附件
            with open(pdf_path, 'rb') as file:
                attachment = MIMEApplication(file.read(), _subtype="pdf")
                attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
                msg.attach(attachment)
        
            # 发送邮件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # 启用TLS加密
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            print(f"报告已成功发送至邮箱: {recipient_email}")
        
        except Exception as e:
            print(f"发送邮件时出错: {e}")

def scheduled_task():
    config = Config()
    print(f"{datetime.now()} - 开始定时任务")
    # 用户配置
    query_config = config.query_config()  
    query = query_config['query']
    category = query_config['category']
    max_results = config.max_results()
    
    # 初始化分析器并处理
    analyzer = ArxivAnalyzer()
    analyzer.process_query(query, category, send_to_email=False, max_results=max_results)
    print(f"{datetime.now()} - 定时任务完成")


    
if __name__ == "__main__":
    # scheduled_task()
    config = Config()
    work_time = config.work_time()['push_hour']
    print(f"{datetime.now()} - 定时任务已设置,将在每天{work_time}点运行")
    # 设置定时任务,每天凌晨运行一次
    print(work_time)
    schedule.every().day.at(work_time).do(scheduled_task)
    
    
    while True:
        print(f"当前本地时间: {datetime.now()}")
        schedule.run_pending()
        time.sleep(600)  # 每隔10min检查一次是否有任务需要运行
