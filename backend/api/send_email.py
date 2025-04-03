from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
import os
import sys
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pydantic import BaseModel
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, root_dir)
from models import Database, Config
router = APIRouter()


config = Config()
email_config = config.email_config()
db = Database(config.db_config())

# 添加请求模型
class SubscribeEmailRequest(BaseModel):
    email: str
    push_time: str

@router.post("/subscribe_success")
async def send_subscribe_email(request: SubscribeEmailRequest, background_tasks: BackgroundTasks):
    """
    发送成功订阅邮件
    """
    print(f"收到订阅成功邮件请求: {request}")

    # 将邮件发送放入后台任务
    background_tasks.add_task(send_email_task, request)
    
    # 立即返回成功响应
    return {"status": "success", "message": "邮件发送任务已加入队列"}

async def send_email_task(request: SubscribeEmailRequest):
    """
    后台发送邮件的任务
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = email_config['sender_email']
        msg['To'] = request.email
        msg['Subject'] = "arXivAgent成功订阅🎉🎉🎉"

        body = f"""您好，

您已成功订阅arXivAgent，我们将在每天的{request.push_time}为您发送arXiv论文分析报告。

此邮件由系统自动发送，请勿回复。
"""
        msg.attach(MIMEText(body, 'plain'))

        smtp_server = email_config['smtp_server']
        smtp_port = email_config['smtp_port']
        sender_email = email_config.get('sender_email')
        sender_password = email_config.get('sender_password')
        
        print(f"尝试连接SMTP服务器: {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)  # 添加超时设置
        server.starttls()
        print("SMTP连接成功")
        
        server.login(sender_email, sender_password)
        print("SMTP登录成功")
        
        server.send_message(msg)
        print(f"邮件成功发送到: {request.email}")
        
        server.quit()
        
    except Exception as e:
        print(f"发送邮件时出错: {str(e)}")
        # 这里可以添加重试逻辑或记录失败日志   