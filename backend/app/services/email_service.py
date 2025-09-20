"""
Email service for sending notifications and password reset emails.
"""
import asyncio
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from ..core.config import settings
from ..core.security import create_password_reset_token


class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_pass = settings.smtp_pass
        self.smtp_use_tls = settings.smtp_use_tls
        self.frontend_url = settings.frontend_url
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.smtp_user
            message["To"] = to_email
            
            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, "plain", "utf-8")
                message.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, "html", "utf-8")
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                start_tls=self.smtp_use_tls,
                username=self.smtp_user,
                password=self.smtp_pass,
            )
            
            return True
        
        except Exception as e:
            # In production, you might want to log this error
            print(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_password_reset_email(
        self,
        email: str,
        display_name: str
    ) -> tuple[bool, Optional[str]]:
        """
        Send password reset email.
        
        Args:
            email: User's email address
            display_name: User's display name
        
        Returns:
            Tuple of (success, reset_token)
        """
        # Generate password reset token
        reset_token = create_password_reset_token(email)
        
        # Create reset URL
        reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"
        
        # Email subject
        subject = "重置您的密码 - 美大客服支持系统"
        
        # HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>密码重置</title>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #ffffff;
                    padding: 30px;
                    border: 1px solid #dee2e6;
                }}
                .button {{
                    display: inline-block;
                    background-color: #007bff;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-radius: 0 0 8px 8px;
                    font-size: 12px;
                    color: #6c757d;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 15px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>美大客服支持系统</h1>
                <h2>密码重置请求</h2>
            </div>
            
            <div class="content">
                <p>亲爱的 {display_name}，</p>
                
                <p>您请求重置您的账户密码。请点击下面的按钮来设置新密码：</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">重置密码</a>
                </div>
                
                <p>或者复制以下链接到浏览器地址栏：</p>
                <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
                    {reset_url}
                </p>
                
                <div class="warning">
                    <strong>重要提醒：</strong>
                    <ul>
                        <li>此链接将在 1 小时后过期</li>
                        <li>如果您没有请求重置密码，请忽略此邮件</li>
                        <li>为了安全，请勿将此链接分享给他人</li>
                    </ul>
                </div>
                
                <p>如果您有任何问题，请联系系统管理员。</p>
                
                <p>
                    此致，<br>
                    美大客服支持系统团队
                </p>
            </div>
            
            <div class="footer">
                <p>此邮件由系统自动发送，请勿直接回复。</p>
                <p>© 2024 美大客服支持系统. 保留所有权利。</p>
            </div>
        </body>
        </html>
        """
        
        # Plain text content
        text_content = f"""
        美大客服支持系统 - 密码重置请求
        
        亲爱的 {display_name}，
        
        您请求重置您的账户密码。请访问以下链接来设置新密码：
        
        {reset_url}
        
        重要提醒：
        - 此链接将在 1 小时后过期
        - 如果您没有请求重置密码，请忽略此邮件
        - 为了安全，请勿将此链接分享给他人
        
        如果您有任何问题，请联系系统管理员。
        
        此致，
        美大客服支持系统团队
        
        ---
        此邮件由系统自动发送，请勿直接回复。
        """
        
        # Send email
        success = await self._send_email(email, subject, html_content, text_content)
        
        return success, reset_token if success else None
    
    async def send_welcome_email(
        self,
        email: str,
        display_name: str,
        temp_password: Optional[str] = None
    ) -> bool:
        """
        Send welcome email to new user.
        
        Args:
            email: User's email address
            display_name: User's display name
            temp_password: Temporary password (if provided)
        
        Returns:
            True if email was sent successfully
        """
        subject = "欢迎加入美大客服支持系统"
        
        password_section = ""
        if temp_password:
            password_section = f"""
            <div class="warning">
                <p><strong>临时密码：</strong> {temp_password}</p>
                <p>请在首次登录后立即修改密码。</p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>欢迎加入</title>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #ffffff;
                    padding: 30px;
                    border: 1px solid #dee2e6;
                }}
                .button {{
                    display: inline-block;
                    background-color: #28a745;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-radius: 0 0 8px 8px;
                    font-size: 12px;
                    color: #6c757d;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 15px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>美大客服支持系统</h1>
                <h2>欢迎加入！</h2>
            </div>
            
            <div class="content">
                <p>亲爱的 {display_name}，</p>
                
                <p>欢迎加入美大客服支持系统！您的账户已经创建成功。</p>
                
                <p><strong>登录信息：</strong></p>
                <ul>
                    <li>邮箱：{email}</li>
                </ul>
                
                {password_section}
                
                <div style="text-align: center;">
                    <a href="{self.frontend_url}" class="button">立即登录</a>
                </div>
                
                <p>系统功能包括：</p>
                <ul>
                    <li>客户问题处理</li>
                    <li>保修信息查询</li>
                    <li>服务中心管理</li>
                    <li>用户权限管理</li>
                </ul>
                
                <p>如果您有任何问题或需要帮助，请联系系统管理员。</p>
                
                <p>
                    此致，<br>
                    美大客服支持系统团队
                </p>
            </div>
            
            <div class="footer">
                <p>此邮件由系统自动发送，请勿直接回复。</p>
                <p>© 2024 美大客服支持系统. 保留所有权利。</p>
            </div>
        </body>
        </html>
        """
        
        return await self._send_email(email, subject, html_content)
    
    async def send_2fa_disabled_notification(
        self,
        email: str,
        display_name: str
    ) -> bool:
        """
        Send notification when 2FA is disabled.
        
        Args:
            email: User's email address
            display_name: User's display name
        
        Returns:
            True if email was sent successfully
        """
        subject = "双因素认证已禁用 - 美大客服支持系统"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>双因素认证已禁用</title>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #ffffff;
                    padding: 30px;
                    border: 1px solid #dee2e6;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-radius: 0 0 8px 8px;
                    font-size: 12px;
                    color: #6c757d;
                }}
                .alert {{
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                    padding: 15px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>美大客服支持系统</h1>
                <h2>安全通知</h2>
            </div>
            
            <div class="content">
                <p>亲爱的 {display_name}，</p>
                
                <div class="alert">
                    <p><strong>重要安全通知：</strong>您的账户的双因素认证（2FA）已被禁用。</p>
                </div>
                
                <p>如果这是您本人操作，请忽略此邮件。</p>
                
                <p>如果您没有进行此操作，请立即：</p>
                <ul>
                    <li>登录您的账户</li>
                    <li>检查账户安全设置</li>
                    <li>重新启用双因素认证</li>
                    <li>联系系统管理员</li>
                </ul>
                
                <p>为了账户安全，我们强烈建议您启用双因素认证。</p>
                
                <p>
                    此致，<br>
                    美大客服支持系统团队
                </p>
            </div>
            
            <div class="footer">
                <p>此邮件由系统自动发送，请勿直接回复。</p>
                <p>© 2024 美大客服支持系统. 保留所有权利。</p>
            </div>
        </body>
        </html>
        """
        
        return await self._send_email(email, subject, html_content) 