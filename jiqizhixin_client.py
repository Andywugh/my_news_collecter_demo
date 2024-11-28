# jiqizhixin_client.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
from logger import LOG
import feedparser

class JiqizhixinClient:
    def __init__(self):
        self.url = 'https://www.jiqizhixin.com/rss'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_articles(self):
        LOG.debug("准备从机器之心 RSS 获取文章。")
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            articles = self.parse_feed(response.text)
            return articles
        except Exception as e:
            LOG.error(f"获取机器之心 RSS feed 失败：{str(e)}")
            return []

    def parse_feed(self, feed_content):
        """解析机器之心的 RSS feed 内容"""
        LOG.debug("解析机器之心 RSS feed 内容。")
        articles = []
        try:
            feed = feedparser.parse(feed_content)
            
            for entry in feed.entries:
                try:
                    # 获取标题
                    title = entry.title.strip()
                    
                    # 获取链接
                    link = entry.link
                    
                    # 获取摘要,处理 CDATA 标签
                    summary = ''
                    if hasattr(entry, 'summary'):
                        soup = BeautifulSoup(entry.summary, 'html.parser')
                        summary = soup.get_text().strip()
                        # 移除多余的空格和换行
                        summary = ' '.join(summary.split())
                    
                    # 获取封面图片
                    cover_image = ''
                    if hasattr(entry, 'content'):
                        content_soup = BeautifulSoup(entry.content[0].value, 'html.parser')
                        img = content_soup.find('img')
                        if img and img.get('src'):
                            cover_image = img['src']
                    
                    # 获取发布时间
                    published = entry.published
                    
                    if title and link:  # 只添加有标题和链接的文章
                        articles.append({
                            'title': title,
                            'summary': summary,
                            'link': link,
                            'cover_image': cover_image,
                            'published': published
                        })
                        LOG.debug(f"成功解析文章：{title}")
                    
                except Exception as e:
                    LOG.warning(f"解析文章条目时出错：{str(e)}")
                    continue
                    
        except Exception as e:
            LOG.error(f"解析 RSS feed 时出错：{str(e)}")
        
        if not articles:
            LOG.warning("未能成功解析任何文章信息")
        else:
            LOG.info(f"成功解析 {len(articles)} 篇机器之心文章。")
        
        return articles

    def export_articles(self, date=None, hour=None):
        LOG.debug("准备导出机器之心的文章。")
        articles = self.fetch_articles()
        
        if not articles:
            LOG.warning("未找到任何机器之心的文章。")
            return None
        
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        if hour is None:
            hour = datetime.now().strftime('%H')

        dir_path = os.path.join('jiqizhixin', date)
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f'{hour}.md')
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(f"# 机器之心最新文章 ({date} {hour}:00)\n\n")
            for idx, article in enumerate(articles, start=1):
                file.write(f"{idx}. [{article['title']}]({article['link']})\n")
                if article['summary']:
                    file.write(f"   - {article['summary']}\n")
                if article['cover_image']:
                    file.write(f"   - ![封面图]({article['cover_image']})\n")
                if article['published']:
                    file.write(f"   - 发布时间: {article['published']}\n")
                file.write("\n")
        
        LOG.info(f"机器之心文章文件生成：{file_path}")
        return file_path


if __name__ == "__main__":
    client = JiqizhixinClient()
    client.export_articles()