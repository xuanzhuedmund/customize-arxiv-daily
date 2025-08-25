from llm import *
from util.request import get_arxiv_papers_from_date
from util.construct_email import (
    framework,
    get_block_html,
    get_empty_html,
    get_stars,
    get_summary_html,
)
from tqdm import tqdm
import json
import os
from datetime import datetime
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import parseaddr, formataddr
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from loguru import logger


class ArxivDaily:
    def __init__(
        self,
        categories: list[str],
        max_entries: int,
        max_paper_num: int,
        provider: str,
        model: str,
        base_url: None,
        api_key: None,
        description: str,
        num_workers: int,
        temperature: float,
        save_dir: None,
        server_chan_key: str = "",
    ):
        self.model_name = model
        self.base_url = base_url
        self.api_key = api_key
        self.max_paper_num = max_paper_num
        self.save_dir = save_dir
        self.num_workers = num_workers
        self.temperature = temperature
        self.server_chan_key = server_chan_key
        self.papers = {}
        for category in categories:
            self.papers[category] = get_arxiv_papers_from_date(category, max_entries, days="pastweek")
            print(
                "{} papers on arXiv for {} are fetched.".format(
                    len(self.papers[category]), category
                )
            )
            # avoid being blocked
            sleep_time = random.randint(5, 15)
            time.sleep(sleep_time)

        provider = provider.lower()
        if provider == "ollama":
            self.model = Ollama(model)
        elif provider == "openai" or provider == "siliconflow":
            self.model = GPT(model, base_url, api_key)
        else:
            assert False, "Model not supported."
        print(
            "Model initialized successfully. Using {} provided by {}.".format(
                model, provider
            )
        )

        self.description = description
        self.lock = threading.Lock()  # 添加线程锁

    def get_response(self, title, abstract):
        prompt = """
            你是一个有帮助的 AI 研究助手，可以帮助我构建论文推荐系统。
            以下是我最近研究领域的描述：
            {}
        """.format(self.description)
        prompt += """
            以下是我从昨天的 arXiv 爬取的论文，我为你提供了标题和摘要：
            标题: {}
            摘要: {}
        """.format(title, abstract)
        prompt += """
            1. 总结这篇论文的主要内容。
            2. 请评估这篇论文与我研究领域的相关性，并给出 0-10 的评分。其中 0 表示完全不相关，10 表示高度相关。
            
            请按以下 JSON 格式给出你的回答：
            {
                "summary": <你的总结>,
                "relevance": <你的评分>
            }
            使用中文回答。
            直接返回上述 JSON 格式，无需任何额外解释。
        """

        response = self.model.inference(prompt, temperature=self.temperature)
        return response

    def process_paper(self, paper, max_retries=5):
        retry_count = 0

        while retry_count < max_retries:
            try:
                title = paper["title"]
                abstract = paper["abstract"]
                response = self.get_response(title, abstract)
                response = response.strip("```").strip("json")
                response = json.loads(response)
                relevance_score = float(response["relevance"])
                summary = response["summary"]
                with self.lock:
                    return {
                        "title": title,
                        "arXiv_id": paper["arXiv_id"],
                        "abstract": abstract,
                        "summary": summary,
                        "relevance_score": relevance_score,
                        "pdf_url": paper["pdf_url"],
                    }
            except Exception as e:
                retry_count += 1
                print(f"处理论文 {paper['arXiv_id']} 时发生错误: {e}")
                print(f"正在进行第 {retry_count} 次重试...")
                if retry_count == max_retries:
                    print(f"已达到最大重试次数 {max_retries}，放弃处理该论文")
                    return None
                time.sleep(1)  # 重试前等待1秒

    def get_recommendation(self):
        recommendations = {}
        for category, papers in self.papers.items():
            for paper in papers:
                recommendations[paper["arXiv_id"]] = paper

        print(
            f"Got {len(recommendations)} non-overlapping papers from yesterday's arXiv."
        )

        recommendations_ = []
        print("Performing LLM inference...")

        with ThreadPoolExecutor(self.num_workers) as executor:
            futures = []
            for arXiv_id, paper in recommendations.items():
                futures.append(executor.submit(self.process_paper, paper))
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Processing papers",
                unit="paper",
            ):
                result = future.result()
                if result:
                    recommendations_.append(result)

        recommendations_ = sorted(
            recommendations_, key=lambda x: x["relevance_score"], reverse=True
        )[: self.max_paper_num]

        # Save recommendation to markdown file
        current_time = datetime.now()
        save_path = os.path.join(
            self.save_dir, f"{current_time.strftime('%Y-%m-%d')}.md"
        )
        # Create the directory if it doesn't exist
        os.makedirs(self.save_dir, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("# Daily arXiv Papers\n")
            f.write(f"## Date: {current_time.strftime('%Y-%m-%d')}\n")
            f.write(f"## Description: {self.description}\n")
            f.write("## Papers:\n")
            for i, paper in enumerate(recommendations_):
                f.write(f"### {i + 1}. {paper['title']}\n")
                f.write(f"#### Abstract:\n")
                f.write(f"{paper['abstract']}\n")
                f.write(f"#### Summary:\n")
                f.write(f"{paper['summary']}\n")
                f.write(f"#### Relevance Score: {paper['relevance_score']}\n")
                f.write(f"#### PDF URL: {paper['pdf_url']}\n")
                f.write("\n")

        return recommendations_

    def summarize(self, recommendations):
        overview = ""
        for i in range(len(recommendations)):
            overview += f"{i + 1}. {recommendations[i]['title']} - {recommendations[i]['summary']} \n"
        prompt = """
            你是一个有帮助的 AI 研究助手，可以帮助我构建论文推荐系统。
            以下是我最近研究领域的描述：
            {}
        """.format(self.description)
        prompt += """
            以下是我从 arXiv 爬取的论文，我为你提供了标题和摘要：
            {}
        """.format(overview)
        prompt += """
            请按以下要求总结论文:

            1. 总体概述
            - 简要总结论文的主要研究领域和热点方向
            - 分析研究趋势和关注重点

            2. 分主题详细分析
            - 将论文按研究主题分类
            - 每个主题下的论文按相关性从高到低排序
            - 对每篇论文按以下格式分析:
                1. 论文标题 (高度相关/相关/一般相关)

                摘要: 非常简要地总结论文的主要内容和创新点。

                相关性分析: 分析该论文与研究领域的关联度,以及对研究的价值。

            3. 总体趋势分析
            - 总结当前研究热点和发展趋势
            - 分析未来可能的研究方向

            请以HTML格式返回,使用中文,包含以下结构:
            <h2>总体概述</h2>
            <p>整体概述内容</p>

            <h2>主题：主题分类的名称</h2>
            <ol>
                <li>论文标题 (相关性)</li>
                <p>摘要: 论文内容总结</p>
                <p>相关性分析: 分析论文价值</p>
                ...
            </ol>

            <h2>总体趋势</h2>
            <ol>
                <li>趋势分析</li>
            </ol>

            <h2>未来研究方向</h2>
            <ol>
                <li>未来研究方向1</li>
                <li>未来研究方向2</li>
                ...
            </ol>

            直接返回HTML内容,无需其他说明。
        """

        response = (
            self.model.inference(prompt, temperature=self.temperature)
            .strip("```")
            .strip("html")
            .strip()
        )
        print(response)
        response = get_summary_html(response)
        return response

    def render_email(self, recommendations):
        parts = []
        if len(recommendations) == 0:
            return framework.replace("__CONTENT__", get_empty_html())
        for i, p in enumerate(tqdm(recommendations, desc="Rendering Emails")):
            rate = get_stars(p["relevance_score"])
            parts.append(
                get_block_html(
                    str(i + 1) + ". " + p["title"],
                    rate,
                    p["arXiv_id"],
                    p["summary"],
                    p["pdf_url"],
                )
            )
        summary = self.summarize(recommendations)
        # Add the summary to the start of the email
        content = summary
        content += "<br>" + "</br><br>".join(parts) + "</br>"
        return framework.replace("__CONTENT__", content)

    def _send_to_server_chan(self, title, desp):
        """
        使用Server酱发送通知，支持多个KEY
        title: 通知标题
        desp: 通知内容
        """
        try:
            import requests

            # Use the key from the constructor
            server_chan_key_str = self.server_chan_key
            Server_chan_KEY = server_chan_key_str.split(',')
            Server_chan_KEY = [key.strip() for key in Server_chan_KEY if key.strip()]

            if not Server_chan_KEY:
                print("未配置Server酱KEY,跳过通知发送")
                return False

            success_count = 0
            for key in Server_chan_KEY:
                try:
                    # Server酱通知接口
                    server_url = f"https://sctapi.ftqq.com/{key}.send"
                    # 构造请求数据
                    data = {"title": title, "desp": desp}
                    # 发送POST请求
                    response = requests.post(server_url, data=data)
                    if response.status_code == 200:
                        print(f"Server酱通知发送成功 (KEY: {key[:4]}...)")
                        success_count += 1
                    else:
                        print(f"Server酱通知发送失败,状态码:{response.status_code} (KEY: {key[:4]}...)")
                except Exception as e:
                    print(f"使用KEY {key[:4]}...发送通知时出错: {str(e)}")
            return success_count > 0
        except Exception as e:
            print(f"发送Server酱通知时出错:{str(e)}")
            return False

    def send_email(
        self,
        sender: str,
        receiver: str,
        password: str,
        smtp_server: str,
        smtp_port: int,
        title: str,
    ):
        recommendations = self.get_recommendation()
        html = self.render_email(recommendations)

        def _format_addr(s):
            name, addr = parseaddr(s)
            return formataddr((Header(name, "utf-8").encode(), addr))

        msg = MIMEText(html, "html", "utf-8")
        msg["From"] = _format_addr(f"{title} <%s>" % sender)

        # 处理多个接收者
        receivers = [addr.strip() for addr in receiver.split(',')]  # Fixed typo: receiver.split(",")
        print(receivers)
        msg["To"] = ",".join([_format_addr(f"You <%s>" % addr) for addr in receivers])

        today = datetime.now().strftime("%Y/%m/%d")
        msg["Subject"] = Header(f"{title} {today}", "utf-8").encode()

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        except Exception as e:
            logger.warning(f"Failed to use TLS. {e}")
            logger.warning(f"Try to use SSL.")
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)

        try:
            server.login(sender, password)
            server.sendmail(sender, receivers, msg.as_string())
            server.quit()
            logger.info("Email sent successfully!")
            self._send_to_server_chan(f"{today}邮件发送成功", f"已成功发送邮件至: {', '.join(receivers)}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            logger.info("Falling back to ServerChan.")
            print(msg.as_string())
            self._send_to_server_chan(f"{title} {today}", msg.as_string())


if __name__ == "__main__":
    categories = ["cs.CV"]
    max_entries = 100
    max_paper_num = 50
    provider = "ollama"
    model = "deepseek-r1:7b"
    description = """
        I am working on the research area of computer vision and natural language processing. 
        Specifically, I am interested in the following fieds:
        1. Object detection
        2. AIGC (AI Generated Content)
        3. Multimodal Large Language Models

        I'm not interested in the following fields:
        1. 3D Vision
        2. Robotics
        3. Low-level Vision
    """

    arxiv_daily = ArxivDaily(
        categories, max_entries, max_paper_num, provider, model, None, None, description, server_chan_key=""
    )
    recommendations = arxiv_daily.get_recommendation()
    print(recommendations)
