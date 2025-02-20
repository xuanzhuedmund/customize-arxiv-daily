from llm import *
from util.request import get_yesterday_arxiv_papers
from util.construct_email import *
from tqdm import tqdm
import json
import os
from datetime import datetime

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
        save_dir: None
    ):
        self.model_name = model
        self.base_url = base_url
        self.api_key = api_key
        self.max_paper_num = max_paper_num
        self.save_dir = save_dir

        self.papers = {}
        for category in categories:
            self.papers[category] = get_yesterday_arxiv_papers(category, max_entries)
            print("{} papers on arXiv for {} are fetched.".format(len(self.papers[category]), category))

        if provider == "ollama" or provider == "Ollama":
            self.provider = "ollama"
            self.model = Ollama(model)
        elif provider == "OpenAI" or provider == "openai" or provider == "siliconflow" or provider == "SiliconFlow":
            self.provider = "openai"
            self.model = GPT(model, base_url, api_key)
        else:
            assert False, "Model not supported."
        print("Model initialized successfully. Using {} provided by {}.".format(model, provider))
        
        self.description = description

    def get_response(self, title, abstract):
        prompt = """
            You are a helpful AI research assistant that can help me build a daily paper recommendation system.
            The following is my description of my recent study area:
            {}
        """.format(self.description)
        prompt += """
            The following is the paper I crwaled from yesterday's arXiv. I provided you with its title, abstract:
            Title: {}
            Abstract: {}
        """.format(title, abstract)
        prompt += """
            1. Summarize the main content of this paper.
            2. Please evaluate the relevance of this paper to my research area and give me a score between 0 and 10. Where 0 means not relevant at all and 10 means highly relevant.
            
            Give your response in the following JSON format:
            {
                "summary": <your_summary>,
                "relevance": <your_score>
            }

            Directly return the above JSON to me without any additional explanation.
        """

        response = self.model.inference(prompt)
        return response
    
    def get_recommendation(self):
        recommendations = {}
        for category, papers in self.papers.items():
            recommendations[category] = []
            print("Analyzing papers in category: {}".format(category))
            for paper in tqdm(papers):
                title = paper["title"]
                abstract = paper["abstract"]
                response = self.get_response(title, abstract)
                try:
                    response = response.strip("```").strip("json")
                    response = json.loads(response)
                    relevance_score = float(response["relevance"])
                    summary = response["summary"]
                    recommendations[category].append({
                        "title": title,
                        "arXiv_id": paper["arXiv_id"],
                        "abstract": abstract,
                        "summary": summary,
                        "relevance_score": relevance_score,
                        "pdf_url": paper["pdf_url"],
                    })
                except Exception as e:
                    print(e)
        
        recommendations_ = []
        for category, papers in recommendations.items():
            recommendations_ += papers

        recommendations_ = sorted(recommendations_, key=lambda x: x["relevance_score"], reverse=True)[:self.max_paper_num]

        # Save recommendation to markdown file
        current_time = datetime.now()
        save_path = os.path.join(self.save_dir, f"{current_time.strftime('%Y-%m-%d')}.md")
        with open(save_path, "w") as f:
            f.write("# Daily arXiv Papers\n")
            f.write(f"## Date: {current_time.strftime('%Y-%m-%d')}\n")
            f.write(f"## Description: {self.description}\n")
            f.write("## Papers:\n")
            for i, paper in enumerate(recommendations_):
                f.write(f"### {i+1}. {paper["title"]}\n")
                f.write(f"#### Abstract:\n")
                f.write(f"{paper["abstract"]}\n")
                f.write(f"#### Summary:\n")
                f.write(f"{paper["summary"]}\n")
                f.write(f"#### Relevance Score: {paper["relevance_score"]}\n")
                f.write(f"#### PDF URL: {paper["pdf_url"]}\n")
                f.write("\n")

        return recommendations_
    
    def summarize(self, recommendations):
        overview = ""
        for i in range(len(recommendations)):
            overview += f"{i+1}. {recommendations[i]['title']} - {recommendations[i]['summary']} \n"
        prompt = """
            You are a helpful AI research assistant that can help me build a daily paper recommendation system.
            The following is my description of my recent study area:
            {}
        """.format(self.description)
        prompt += """
            The following is the paper I crwaled from yesterday's arXiv. I provided you with its title, abstract:
            {}
        """.format(overview)
        prompt += """
            Please help to summarize today's papers and give me a brief overview of the papers.
            Return your response in HTML format.
        """

        response = self.model.inference(prompt).strip("```").strip("html").strip()
        return response
    
    def render_email(self, recommendations):
        parts = []
        if len(recommendations) == 0:
            return framework.replace('__CONTENT__', get_empty_html())
        for p in tqdm(recommendations, desc="Rendering Emails"):
            rate = get_stars(p["relevance_score"])
            parts.append(get_block_html(p["title"], rate, p["arXiv_id"], p["summary"], p["pdf_url"]))

        summary = self.summarize(recommendations)
        # Add the summary to the start of the email
        content = summary
        content += '<br>' + '</br><br>'.join(parts) + '</br>'
        return framework.replace('__CONTENT__', content)
    
    def send_email(self, sender:str, receiver:str, password:str,smtp_server:str,smtp_port:int):
        recommendations = self.get_recommendation()
        html = self.render_email(recommendations)

        def _format_addr(s):
            name, addr = parseaddr(s)
            return formataddr((Header(name, 'utf-8').encode(), addr))

        msg = MIMEText(html, 'html', 'utf-8')
        msg['From'] = _format_addr('Github Action <%s>' % sender)
        msg['To'] = _format_addr('You <%s>' % receiver)
        today = datetime.now().strftime('%Y/%m/%d')
        msg['Subject'] = Header(f'Daily arXiv {today}', 'utf-8').encode()

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

    arxiv_daily = ArxivDaily(categories, max_entries, max_paper_num, provider, model, None, None, description)
    recommendations = arxiv_daily.get_recommendation()
    print(recommendations)