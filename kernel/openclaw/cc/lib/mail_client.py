"""
邮件客户端 - 用于发送Patch到KVM邮件列表
"""
import os
import subprocess
import smtplib
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PatchEmail:
    """Patch邮件"""
    subject: str
    body: str
    from_email: str
    to_list: List[str]
    cc_list: List[str] = None
    attachments: List[str] = None


class MailClient:
    """邮件客户端"""

    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = 587,
        username: str = None,
        password: str = None,
        from_name: str = None,
        from_email: str = None
    ):
        self.smtp_server = smtp_server or os.environ.get('SMTP_SERVER')
        self.smtp_port = smtp_port
        self.username = username or os.environ.get('SMTP_USERNAME')
        self.password = password or os.environ.get('SMTP_PASSWORD')
        self.from_name = from_name or os.environ.get('EMAIL_FROM_NAME', 'RISC-V Developer')
        self.from_email = from_email or os.environ.get('EMAIL_FROM', 'dev@riscv-kvm.org')

    def send_email(self, email: PatchEmail) -> bool:
        """发送邮件"""
        msg = MIMEMultipart()
        msg['Subject'] = email.subject
        msg['From'] = f'{self.from_name} <{self.from_email}>'
        msg['To'] = ', '.join(email.to_list)

        if email.cc_list:
            msg['Cc'] = ', '.join(email.cc_list)

        msg.attach(MIMEText(email.body, 'plain'))

        # 添加附件
        if email.attachments:
            for attachment in email.attachments:
                self._add_attachment(msg, attachment)

        # 发送邮件
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                recipients = email.to_list + (email.cc_list or [])
                server.send_message(msg, self.from_email, recipients)
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def _add_attachment(self, msg: MIMEMultipart, filepath: str):
        """添加附件"""
        with open(filepath, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {os.path.basename(filepath)}'
        )
        msg.attach(part)


class GitSendEmailClient:
    """使用git send-email发送邮件"""

    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or os.getcwd()

    def send_patch(
        self,
        patch_file: str,
        to: str,
        cc: List[str] = None,
        subject: str = None
    ) -> bool:
        """使用git send-email发送patch"""
        cmd = ['git', 'send-email', patch_file, '--to', to]

        if cc:
            for cc_addr in cc:
                cmd.extend(['--cc', cc_addr])

        if subject:
            cmd.extend(['--subject', subject])

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Failed to send patch: {e}")
            return False

    def send_series(
        self,
        patch_dir: str,
        to: str,
        cc: List[str] = None,
        cover_letter: str = None
    ) -> bool:
        """发送补丁系列"""
        cmd = ['git', 'send-email', patch_dir, '--to', to]

        if cc:
            for cc_addr in cc:
                cmd.extend(['--cc', cc_addr])

        if cover_letter:
            cmd.extend(['--cover-letter', '--cover-letter-description', cover_letter])

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Failed to send patch series: {e}")
            return False


# KVM邮件列表常量
KVM_LIST = 'kvm@vger.kernel.org'
LINUX_RISC_V_LIST = 'linux-riscv@lists.infradead.org'
MAINTAINERS = {
    'riscv': 'linux-riscv@lists.infradead.org',
    'kvm-riscv': 'kvm@lists.linux.dev'
}


def create_patch_email(
    feature: str,
    version: str,
    cover_letter: str,
    patch_files: List[str],
    to_list: str = KVM_LIST,
    cc_list: List[str] = None
) -> PatchEmail:
    """创建patch邮件"""
    subject = f'[PATCH v{version}] riscv: KVM: {feature}'

    body = f"""Hi,

{cover_letter}

---
以下为patch内容：
"""

    return PatchEmail(
        subject=subject,
        body=body,
        from_email='dev@riscv-kvm.org',
        to_list=[to_list],
        cc_list=cc_list,
        attachments=patch_files
    )
