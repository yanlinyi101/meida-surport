// Cloudflare Pages中间件
// 处理所有请求并转发到我们的应用

export async function onRequest(context) {
  // 获取请求对象
  const request = context.request;
  const url = new URL(request.url);
  const path = url.pathname;
  
  // 处理静态文件请求
  if (path.startsWith('/static/')) {
    // 静态文件直接从Cloudflare Pages提供
    return context.next();
  }
  
  try {
    // 导入主应用
    const { default: app } = await import('../cloudflare.js');
    
    // 处理请求
    return await app.handle(request);
  } catch (error) {
    // 错误处理
    return new Response(`Server Error: ${error.message}`, {
      status: 500,
      headers: { 'Content-Type': 'text/plain' }
    });
  }
} 