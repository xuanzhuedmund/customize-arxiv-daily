"""
Use requests and BeautifulSoup to get yesterday's arXiv papers.
"""

import requests
from bs4 import BeautifulSoup
import time

def get_arxiv_papers_from_date(category: str = "physics.optics", max_results: int = 1000, days: str = "pastweek"):  

    if days == "yesterday": # 昨天
        url = f"https://arxiv.org/list/{category}/new?skip=0&show={max_results}"
        response = requests.get(url)

        soup = BeautifulSoup(response.text, "html.parser")

        try:
            entries = soup.find_all("dl", id="articles")[0].find_all(["dt", "dd"])
        except Exception as e:
            return []

        papers = []
        for i in range(0, len(entries), 2):
            title_tag = entries[i + 1].find("div", class_="list-title")
            title = (
                title_tag.text.strip().replace("Title:", "").strip()
                if title_tag
                else "No title available"
            )

            abs_url = "https://arxiv.org" + entries[i].find("a", title="Abstract")["href"]

            pdf_url = entries[i].find("a", title="Download PDF")["href"]
            pdf_url = "https://arxiv.org" + pdf_url

            abstract_tag = entries[i + 1].find("p", class_="mathjax")
            abstract = (
                abstract_tag.text.strip() if abstract_tag else "No abstract available"
            )

            comments_tag = entries[i + 1].find("div", class_="list-comments")
            comments = (
                comments_tag.text.strip() if comments_tag else "No comments available"
            )

            paper_info = {
                "title": title,
                "arXiv_id": pdf_url.split("/")[-1],
                "abstract": abstract,
                "comments": comments,
                "pdf_url": pdf_url,
                "abstract_url": abs_url,
            }

            papers.append(paper_info)

        return papers
        
    elif days == "pastweek": # 过去一周
        # 获取所有论文，需要处理多个dl元素
        all_papers = []
        skip = 0
        batch_size = 2000  # 每页最多2000条
        
        while True:
            url = f"https://arxiv.org/list/{category}/pastweek?skip={skip}&show={batch_size}"
            response = requests.get(url)
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            papers_on_this_page = 0
            limit_reached = False
            try:
                # 获取所有dl元素，每个都可能包含论文
                dl_elements = soup.find_all("dl", id="articles")
                
                # 处理所有dl元素中的论文
                for dl in dl_elements:
                    entries = dl.find_all(["dt", "dd"])
                    papers_on_this_page += len(entries)
                    
                    for i in range(0, len(entries), 2):
                        if i + 1 >= len(entries):
                            break
                            
                        title_tag = entries[i + 1].find("div", class_="list-title")
                        title = (
                            title_tag.text.strip().replace("Title:", "").strip()
                            if title_tag
                            else "No title available"
                        )

                        abs_url = "https://arxiv.org" + entries[i].find("a", title="Abstract")["href"]

                        pdf_url = entries[i].find("a", title="Download PDF")["href"]
                        pdf_url = "https://arxiv.org" + pdf_url

                        abstract_tag = entries[i + 1].find("p", class_="mathjax")
                        abstract = (
                            abstract_tag.text.strip() if abstract_tag else "No abstract available"
                        )

                        comments_tag = entries[i + 1].find("div", class_="list-comments")
                        comments = (
                            comments_tag.text.strip() if comments_tag else "No comments available"
                        )

                        paper_info = {
                            "title": title,
                            "arXiv_id": pdf_url.split("/")[-1],
                            "abstract": abstract,
                            "comments": comments,
                            "pdf_url": pdf_url,
                            "abstract_url": abs_url,
                        }

                        all_papers.append(paper_info)
                        if len(all_papers) >= max_results:
                            limit_reached = True
                            break
                    if limit_reached:
                        break
            except Exception as e:
                break
            
            # If the limit is reached, or the page is empty, or it's the last page, exit the loop.
            if limit_reached or papers_on_this_page == 0 or papers_on_this_page < (batch_size * 2):
                break
                
            skip += batch_size
            time.sleep(1)  # 避免请求过于频繁
        
        return all_papers[:max_results]


if __name__ == "__main__":
    papers = get_arxiv_papers_from_date()
    print(f"获取的论文数量: {len(papers)}")
