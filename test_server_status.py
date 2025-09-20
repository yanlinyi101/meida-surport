"""
测试服务器启动状态
"""
import time
import sys

def test_server_connection():
    """测试服务器连接"""
    print("🚀 等待服务器启动...")
    
    # 等待服务器启动
    for i in range(15):
        print(f"等待中... ({i+1}/15)")
        time.sleep(2)
        
        try:
            import requests
            response = requests.get("http://127.0.0.1:8000/health", timeout=3)
            if response.status_code == 200:
                print("✅ 服务器启动成功！")
                print(f"健康检查响应: {response.json()}")
                
                # 测试主要页面
                test_pages = [
                    ("用户端首页", "http://127.0.0.1:8000/"),
                    ("管理后台", "http://127.0.0.1:8000/admin"),
                    ("API文档", "http://127.0.0.1:8000/api/docs")
                ]
                
                print("\n📍 页面测试结果:")
                for name, url in test_pages:
                    try:
                        resp = requests.get(url, timeout=5)
                        status = "✅ 正常" if resp.status_code == 200 else f"⚠️ 状态码: {resp.status_code}"
                        print(f"   {name}: {status}")
                    except Exception as e:
                        print(f"   {name}: ❌ 访问失败 - {e}")
                
                print("\n🎉 系统已成功启动！")
                print("\n📍 访问地址:")
                print("   - 用户端首页: http://127.0.0.1:8000/")
                print("   - 管理后台: http://127.0.0.1:8000/admin")
                print("   - API文档: http://127.0.0.1:8000/api/docs")
                print("\n🔑 默认管理员账号:")
                print("   邮箱: admin@meidasupport.com")
                print("   密码: admin123456")
                return True
                
        except ImportError:
            print("❌ requests模块未安装，无法测试连接")
            return False
        except Exception as e:
            if i < 14:  # 不是最后一次尝试
                continue
            else:
                print(f"❌ 服务器连接失败: {e}")
    
    print("❌ 服务器启动超时")
    print("💡 请检查控制台输出中的错误信息")
    return False

if __name__ == "__main__":
    success = test_server_connection()
    sys.exit(0 if success else 1) 