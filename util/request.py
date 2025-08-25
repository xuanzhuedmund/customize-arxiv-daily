"""
Use requests and BeautifulSoup to get yesterday's arXiv papers.
"""

import requests
from bs4 import BeautifulSoup
import time

def get_arxiv_papers_from_date(category: str = "physics.optics", max_results: int = 10, days: str = "pastweek"):  

    if days == "yesterday": # 昨天
        url = f"https://arxiv.org/list/{category}/new?skip=0&show={max_results}"
        time.sleep(1)
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
            # 构建用于获取过去一周论文列表的URL。
            # {category}: 论文的类别，例如 'cs.CV' 或 'physics.optics'。
            # skip={skip}: 用于分页，跳过已经获取的论文数量。
            # show={batch_size}: 指定每页显示的最大论文数量。
            url = f"https://arxiv.org/list/{category}/pastweek?skip={skip}&show={batch_size}"
            # 发送HTTP GET请求到构建好的URL，获取页面内容。
            time.sleep(1)
            response = requests.get(url)
            
            # 使用BeautifulSoup库和Python内置的html.parser来解析返回的HTML文本。
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 初始化当前页面上找到的论文数量的计数器。
            papers_on_this_page = 0
            # 初始化一个标志，用于判断是否已经收集到足够数量的论文。
            limit_reached = False
            try:
                # 获取所有dl元素，每个都可能包含论文
                # 在 arXiv 的论文列表页面 (如 /list/cs/new), 论文按日期分组。
                # 每个日期分组都包含在一个 <dl> 标签中。
                # 这行代码找到页面上所有的 <dl> 标签，以便处理所有日期的论文。
                dl_elements = soup.find_all("dl", id="articles")
                
                # 遍历每个日期的论文列表（即每个 <dl> 标签）。
                for dl in dl_elements:
                    # 在一个 <dl> 标签内，每篇论文由一对 <dt> 和 <dd> 标签表示。
                    # <dt> 标签包含论文的链接（如摘要页、PDF）。
                    # <dd> 标签包含论文的详细信息（如标题、作者、摘要内容）。
                    # 这行代码按顺序找到所有的 <dt> 和 <dd> 标签。
                    entries = dl.find_all(["dt", "dd"])
                    papers_on_this_page += len(entries)
                    
                    # `entries` 列表是扁平的: [dt1, dd1, dt2, dd2, ...]。
                    # 我们以2为步长进行迭代，以便成对处理 (dt, dd)。
                    for i in range(0, len(entries), 2):
                        if i + 1 >= len(entries):
                            break
                            
                        # <dd> 标签 (位于索引 i + 1) 包含论文的详细信息。
                        # 标题位于一个 class="list-title" 的 <div> 中。
                        # HTML 示例: <div class="list-title"><span class="descriptor">Title:</span> Some Paper Title</div>
                        title_tag = entries[i + 1].find("div", class_="list-title")
                        title = (
                            title_tag.text.strip().replace("Title:", "").strip()
                            if title_tag
                            else "No title available"
                        )

                        # <dt> 标签 (位于索引 i) 包含论文的链接。
                        # 摘要页链接是一个 title="Abstract" 的 <a> 标签。
                        # HTML 示例: <a href="/abs/2508.06215" title="Abstract">arXiv:2508.06215</a>
                        abs_url = "https://arxiv.org" + entries[i].find("a", title="Abstract")["href"]

                        # PDF 链接是一个 title="Download PDF" 的 <a> 标签。
                        # HTML 示例: <a href="/pdf/2508.06215" title="Download PDF">pdf</a>
                        pdf_url = entries[i].find("a", title="Download PDF")["href"]
                        pdf_url = "https://arxiv.org" + pdf_url
                        # 发送HTTP GET请求到构建好的URL，获取页面内容。
                        time.sleep(1)
                        abs_response = requests.get(abs_url)
                        
                        # 使用BeautifulSoup库和Python内置的html.parser来解析返回的HTML文本。
                        abs_soup = BeautifulSoup(abs_response.text, "html.parser")
                        # HTML 示例: <blockquote class="mathjax">Selective spatial control of chemical reactions...</p>
                        abstract_tag = abs_soup.find("blockquote", class_="abstract mathjax")
                        abstract = (
                            abstract_tag.text.strip().replace("Abstract:", "").strip() 
                            if abstract_tag 
                            else "No abstract available"
                        )

                        # 评论（如果有）位于 <dd> 标签内的一个 class="list-comments" 的 <div> 中。
                        # HTML 示例: <div class="list-comments mathjax">10 pages, 5 figures</div>
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
    for i, paper in enumerate(papers):
        print(f"\n--- 论文 {i+1} ---")
        print(f"标题: {paper['title']}")
        print(f"arXiv ID: {paper['arXiv_id']}")
        print(f"摘要链接: {paper['abstract_url']}")
        print(f"PDF 链接: {paper['pdf_url']}")
        print(f"摘要: {paper['abstract']}")
        print(f"评论: {paper['comments']}")
        print("-" * 20)
