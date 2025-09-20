// Cloudflare Pages API处理函数
// 处理所有API请求

import { app } from '../main.py';
import { create_cloudflare_adapter } from '../cloudflare_adapter.py';

export async function onRequest(context) {
  try {
    // 创建适配器
    const adapter = create_cloudflare_adapter(app);
    
    // 处理请求
    const response = await adapter(context.request);
    
    // 返回响应
    return new Response(response.body, {
      status: response.status,
      headers: response.headers
    });
  } catch (error) {
    // 错误处理
    return new Response(`API Error: ${error.message}`, {
      status: 500,
      headers: { 'Content-Type': 'text/plain' }
    });
  }
} 