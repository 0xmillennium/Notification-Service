import logging
import aiosmtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, DictLoader
from typing import Dict, Optional, Any
from src import config

logger = logging.getLogger(__name__)


class AbstractEmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    async def send_email(self, 
                        to_email: str, 
                        subject: str, 
                        content: str, 
                        template_vars: Dict[str, str] = None) -> bool:
        """Send an email and return success status."""
        pass


class SMTPEmailProvider(AbstractEmailProvider):
    """SMTP email provider using aiosmtplib."""
    
    def __init__(self, 
                 smtp_host: str, 
                 smtp_port: int, 
                 username: str, 
                 password: str,
                 start_tls: bool = True,
                 from_email: str = None):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.start_tls = start_tls
        self.from_email = from_email or username
        
        # Simple email templates
        self.templates = Environment(loader=DictLoader({
            'email_verification': '''
            <html>
            <body>
            <h2>Email Verification Required</h2>
            <p>Hi {{username}},</p>
            <p>Please verify your email address by clicking the link below:</p>
            <p><a href="{{verification_link}}">Verify Email</a></p>
            <p>Best regards,<br>{{service_name}} Team</p>
            </body>
            </html>
            ''',
            
            'password_reset': '''
            <html>
            <body>
            <h2>Password Reset Request</h2>
            <p>Hi,</p>
            <p>You requested a password reset. Click the link below to reset your password:</p>
            <p><a href="{{reset_link}}">Reset Password</a></p>
            <p>If you didn't request this, please ignore this email.</p>
            <p>Best regards,<br>{{service_name}} Team</p>
            </body>
            </html>
            ''',
            
            'welcome': '''
            <html>
            <body>
            <h2>Welcome to {{service_name}}!</h2>
            <p>Hi,</p>
            <p>Welcome to our platform! We're excited to have you on board.</p>
            <p>Best regards,<br>{{service_name}} Team</p>
            </body>
            </html>
            ''',
            
            'security_alert': '''
            <html>
            <body>
            <h2>Security Alert</h2>
            <p>Hi,</p>
            <p>{{alert_message}}</p>
            <p>If this wasn't you, please contact support immediately.</p>
            <p>Best regards,<br>{{service_name}} Team</p>
            </body>
            </html>
            '''
        }))

    async def send_email(self, 
                        to_email: str, 
                        subject: str, 
                        content: str, 
                        template_vars: Dict[str, Any] = None) -> bool:
        """
        Send an email using SMTP with template rendering.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email content or template name
            template_vars: Variables for template rendering
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = self.from_email
            message['To'] = to_email
            message['Subject'] = subject
            
            # Render template if template_vars provided and content is a template name
            if template_vars and content in self.templates.list_templates():
                template = self.templates.get_template(content)
                html_content = template.render(**template_vars)
            else:
                html_content = content
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                start_tls=self.start_tls,
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False


def create_email_provider() -> AbstractEmailProvider:
    """Factory function to create email provider from config."""
    return SMTPEmailProvider(
        smtp_host=config.get_smtp_host(),
        smtp_port=config.get_smtp_port(),
        username=config.get_smtp_username(),
        password=config.get_smtp_password(),
        start_tls=config.get_smtp_start_tls(),
        from_email=config.get_smtp_from_email()
    )
