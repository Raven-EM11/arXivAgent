import { ENV_CONFIG } from '@/config/env';

export type Paper = {
  entry_id: string;
  title: string;
  abstract: string;
  category: string;
  publishedAt: Date;
}

export async function submitSearchRequest(data: {
  email: string;
  topics: string[];
  query_content: string;
  push_time: string;
}) {
  // 添加调试日志
  console.log('发送请求到:', `${ENV_CONFIG.API_BASE_URL}/search-request`);
  console.log('请求数据:', data);
  
  const response = await fetch(`${ENV_CONFIG.API_BASE_URL}/search-request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  // 打印响应状态和内容
  console.log('响应状态:', response.status);
  const responseText = await response.text();
  console.log('响应内容:', responseText);

  // 尝试解析 JSON
  try {
    return JSON.parse(responseText);
  } catch (error) {
    console.error('JSON 解析错误:', error);
    throw new Error(`服务器返回了非JSON响应: ${responseText.substring(0, 100)}...`);
  }
}

export async function fetchLatestPapers(category: string = 'all'): Promise<Paper[]> {
  try {
    const response = await fetch(`${ENV_CONFIG.API_BASE_URL}/papers?category=${category}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to fetch papers');
    }

    const data = await response.json();
    
    // 转换日期字符串为 Date 对象
    return data.map((paper: any) => ({
      ...paper,
      publishedAt: new Date(paper.publishedAt),
    }));

  } catch (error) {
    console.error('Error fetching papers:', error);
    throw error;
  }
}

export async function translatePaper(entryId: string): Promise<Paper> {
  // 从完整URL中提取ID部分
  const pureId = entryId.split('/').pop() || '';
  
  const response = await fetch(`${ENV_CONFIG.API_BASE_URL}/papers/${pureId}/translate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to translate paper');
  }

  const data = await response.json();
  return {
    ...data,
    publishedAt: new Date(data.publishedAt),
  };
}

export async function sendSubscribeSuccessEmail(email: string, pushTime: string) {
  const response = await fetch(`${ENV_CONFIG.API_BASE_URL}/subscribe_success`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, push_time: pushTime }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || '发送订阅成功邮件失败');
  }

  return response.json();
}

