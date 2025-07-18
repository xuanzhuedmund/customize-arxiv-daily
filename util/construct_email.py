import math
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import smtplib
import datetime
from loguru import logger

framework = """
<!DOCTYPE HTML>
<html>
<head>
  <style>
    .star-wrapper {
      font-size: 1.3em; /* 调整星星大小 */
      line-height: 1; /* 确保垂直对齐 */
      display: inline-flex;
      align-items: center; /* 保持对齐 */
    }
    .half-star {
      display: inline-block;
      width: 0.5em; /* 半颗星的宽度 */
      overflow: hidden;
      white-space: nowrap;
      vertical-align: middle;
    }
    .full-star {
      vertical-align: middle;
    }
  </style>
</head>
<body>

<div>
    __CONTENT__
</div>

<br><br>
<div>
To unsubscribe, remove your email in your Github Action setting.
</div>

</body>
</html>
"""


def get_empty_html():
    block_template = """
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
  <tr>
    <td style="font-size: 20px; font-weight: bold; color: #333;">
        No Papers Today. Take a Rest!
    </td>
  </tr>
  """
    return block_template


def get_summary_html(summary: str):
    summary = summary.replace("{", "{{").replace("}", "}}")
    style = """
        <style>
            h2 {
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 12px;
                margin: 25px 0 20px 0;
                font-size: 28px;
                font-weight: bold;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            }
            p {
                color: #34495e;
                line-height: 1.8;
                margin: 15px 0;
                font-size: 16px;
            }
            ol {
                color: #34495e;
                line-height: 1.8;
                font-size: 16px;
            }
            li {
                margin: 15px 0;
                font-size: 16px;
            }
            .paper-title {
                color: #2980b9;
                font-weight: bold;
                font-size: 20px;
            }
            .relevance {
                color: #e74c3c;
                font-style: italic;
                font-size: 18px;
                font-weight: bold;
            }
            .abstract, .analysis {
                margin-left: 25px;
                color: #2c3e50;
                font-size: 16px;
                line-height: 1.8;
            }
        </style>
    """
    summary = summary.replace("</head>", f"{style}</head>")
    return summary


def get_block_html(title: str, rate: str, arxiv_id: str, abstract: str, pdf_url: str):
    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Relevance:</strong> {rate}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>arXiv ID:</strong> {arxiv_id}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {abstract}
        </td>
    </tr>

    <tr>
        <td style="padding: 8px 0;">
            <a href="{pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #d9534f; padding: 8px 16px; border-radius: 4px;">PDF</a>
        </td>
    </tr>
</table>
"""
    return block_template.format(
        title=title, rate=rate, arxiv_id=arxiv_id, abstract=abstract, pdf_url=pdf_url
    )


def get_stars(score: float):
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'
    low = 2
    high = 8
    if score <= low:
        return ""
    elif score >= high:
        return full_star * 5
    else:
        interval = (high - low) / 10
        star_num = math.ceil((score - low) / interval)
        full_star_num = int(star_num / 2)
        half_star_num = star_num - full_star_num * 2
        return (
            '<div class="star-wrapper">'
            + full_star * full_star_num
            + half_star * half_star_num
            + "</div>"
        )


def send_email(
    sender: str,
    receiver: str,
    password: str,
    smtp_server: str,
    smtp_port: int,
    html: str,
):
    def _format_addr(s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, "utf-8").encode(), addr))

    msg = MIMEText(html, "html", "utf-8")
    msg["From"] = _format_addr("Github Action <%s>" % sender)
    msg["To"] = _format_addr("You <%s>" % receiver)
    today = datetime.datetime.now().strftime("%Y/%m/%d")
    msg["Subject"] = Header(f"Daily arXiv {today}", "utf-8").encode()

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
    except Exception as e:
        logger.warning(f"Failed to use TLS. {e}")
        logger.warning(f"Try to use SSL.")
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)

    server.login(sender, password)
    server.sendmail(sender, [receiver], msg.as_string())
    server.quit()
