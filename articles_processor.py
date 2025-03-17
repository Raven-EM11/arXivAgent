from models import LLMModel, Article, Config
from utils.logger import Logger

import re
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime
import imgkit

import pdfkit
from PyPDF2 import PdfMerger
import oss2
import tempfile
import shutil

logger = Logger.get_logger('articles_processor')

class ArticlePostProcessor:
    """文章后处理器，负责生成最终报告和结构化数据"""
    def __init__(self, llm: LLMModel):
        self.llm = llm
        # 设置Jinja2环境
        template_dir = os.path.join(os.path.dirname(__file__), 'template')
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        self.config = Config()

    
    def generate_html_report(self, article: Article, analysis: dict, template_name: str = 'default.html') -> str:
        """生成HTML格式的分析报告"""
        template = self.jinja_env.get_template(template_name)
        
        # 准备模板数据
        template_data = {
            'title': article.title,
            'title_cn': article.CN_title,
            'article_url': article.entry_id,
            'abstract': article.CN_summary,
            'summary': analysis['article_summary'],
            'rating_score': analysis['rating_score'],
            'rating_details': {
                "创新性": {
                    "score": float(analysis['rating_details']["创新性"]["score"]),
                    "description": analysis['rating_details']["创新性"]["description"] 
                },
                "写作质量": {
                    "score": float(analysis['rating_details']["写作质量"]["score"]),
                    "description": analysis['rating_details']["写作质量"]["description"]
                },
                "相关程度": {
                    "score": float(analysis['rating_details']["相关程度"]["score"]),
                    "description": analysis['rating_details']["相关程度"]["description"]
                }
            },
            'first_author': article.author_and_affiliation.get('first_author', ''),  # 添加第一作者
            'author_institutions': article.author_and_affiliation.get('author_institutions', []),  # 添加作者机构信息
            'update_time': datetime.now().strftime('%Y年%m月%d日 %H:%M')
        }
        
        return template.render(**template_data)
    
    def _parse_rating_text(self, rating_text: str) -> dict:
        """解析评分文本为结构化数据"""
        result = {}
        # 按行分割
        lines = rating_text.split('\n')
        
        for line in lines:
            if ':' in line:
                category, rest = line.split(':', 1)
                category = category.strip()
                
                # 分割分数和描述
                if '-' in rest:
                    score_str, description = rest.split('-', 1)
                    try:
                        score = float(score_str.strip())
                    except ValueError:
                        score = 0.0
                        
                    result[category] = {
                        'score': score,
                        'description': description.strip()
                    }
        
        return result

    def export_to_image(self, html_content, output_path):
        """将HTML导出为移动端样式的图片"""
        options = {
        'format': 'png',
        # 核心参数：缩放倍数与分辨率配合
        'zoom': 2,          # 关键！2倍缩放相当于2倍物理像素
        'width': 1248,       # 逻辑像素（与移动端viewport同尺寸）
        
        # 可选质量增强参数
        'quality': 100,     # 适用于jpeg格式
        
        # 渲染引擎优化
        'disable-smart-width': '',
        'enable-local-file-access': None  # 允许加载本地资源
        }
        
        imgkit.from_string(html_content, output_path, options=options)

    def export_to_pdf(self, html_content, output_path):
        """将HTML导出为PDF格式"""
        options = {
            'page-size': 'A4',
            'margin-top': '0.1in',
            'margin-right': '0.1in',
            'margin-bottom': '0.2in',
            'margin-left': '0.1in',
            'zoom': 1.2,
            'encoding': 'UTF-8',
            'quiet': '',
            'enable-local-file-access': None,
            'dpi': 500,
            'image-quality': 100,
            'header-font-size': '8',
            'footer-font-size': '8',
            'enable-smart-shrinking': '',
        }
        
        try:
            pdfkit.from_string(html_content, output_path, options=options)
            logger.info(f"成功导出PDF到: {output_path}")
        except Exception as e:
            logger.error(f"导出PDF时出错: {e}")

    def upload_to_oss(self, file_path: str, oss_key: str) -> str:
        """上传文件到OSS并返回访问URL
        
        Args:
            file_path: 本地文件路径
            oss_key: OSS中的文件键名
            
        Returns:
            str: 文件的访问URL
        """
        try:
            with open(file_path, 'rb') as f:
                self.bucket.put_object(oss_key, f)
            url = self.bucket.sign_url('GET', oss_key, 60*60*24)
            logger.info(f"成功上传文件到OSS: {oss_key}")
            return url
        except Exception as e:
            logger.error(f"上传到OSS时出错: {e}")
            return None

    def process_article(self, article:Article, query:str, template_name: str = 'v1.html', output_dir: str = None, report_type: str = 'pdf'):
            """处理单篇文章，生成分析报告并导出为图片和PDF
            
            Args:
                article: Article对象
                query: 查询字符串
                template_name: 模板文件名
                output_dir: 输出目录路径，如果为None则使用默认路径
            """
            # 生成分析内容
            analysis = article.generate_analysis(query, self.llm)
            
            # 使用传入的输出目录或默认目录
            if not output_dir:
                output_dir = os.path.abspath("./analysis_report")
            os.makedirs(output_dir, exist_ok=True)
            
            # 清理文件名，移除可能导致问题的特殊字符
            safe_id = re.sub(r'[^\w\-_.]', '_', article.entry_id.split('/')[-1])
            png_output_path = os.path.join(output_dir, f"report_{safe_id}.png")
            pdf_output_path = os.path.join(output_dir, f"report_{safe_id}.pdf")
            
            # 生成HTML报告
            html_report = self.generate_html_report(article, analysis, template_name=template_name)
            
            # 导出为PNG和PDF
            if report_type == 'pdf':
                self.export_to_pdf(html_report, pdf_output_path)
            else:
                self.export_to_image(html_report, png_output_path)
            
            return analysis
    def merge_pdfs(self, pdf_files, output_path):
            """
            将多个PDF文件合并成一个PDF文件
            
            参数:
            - pdf_files: PDF文件路径列表
            - output_path: 输出的合并PDF文件路径
            
            返回:
            - bool: 合并是否成功
            """
            try:
                merger = PdfMerger()
                
                # 检查所有文件是否存在
                for pdf_file in pdf_files:
                    if not os.path.exists(pdf_file):
                        print(f"文件不存在: {pdf_file}")
                        return False
                
                # 按顺序合并PDF文件
                for pdf_file in pdf_files:
                    try:
                        merger.append(pdf_file)
                        print(f"成功添加文件: {pdf_file}")
                    except Exception as e:
                        print(f"添加文件时出错 {pdf_file}: {e}")
                        continue
                
                # 保存合并后的文件
                merger.write(output_path)
                merger.close()
                
                print(f"PDF文件成功合并到: {output_path}")
                return True
                
            except Exception as e:
                print(f"合并PDF文件时出错: {e}")
                return False
            finally:
                if 'merger' in locals():
                    merger.close()

    