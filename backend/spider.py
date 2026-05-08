import requests
from models import db, Website

def auto_fetch_hacker_news(app):
    """
    Hacker News 热门项目自动采集器
    """
    with app.app_context():
        print("🤖 [爬虫启动] 正在潜入 Hacker News 获取全球热门项目...")
        
        try:
            # 1. 抓取当前最热的帖子 ID 列表（取前 30 个）
            top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            ids = requests.get(top_ids_url, timeout=10).json()[:30] 
            
            new_count = 0
            
            # 2. 遍历每一个帖子 ID 获取详情
            for item_id in ids:
                detail_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
                item = requests.get(detail_url, timeout=10).json()
                
                # 3. 核心过滤逻辑：只有包含实体 URL 的才算网站项目
                if item and 'url' in item:
                    url = item['url']
                    title = item.get('title', '未命名开源项目')
                    
                    # 4. 查重防撞：去数据库看一眼这个 URL 是不是已经收录过了
                    exist_site = Website.query.filter_by(url=url).first()
                    
                    if not exist_site:
                        # 5. 发现新大陆！装入待审核池
                        new_site = Website(
                            name=title,
                            url=url,
                            description=f"HN 得分: {item.get('score', 0)} | 自动采集自 Hacker News",
                            status='pending',
                            source='Hacker News'
                        )
                        db.session.add(new_site)
                        new_count += 1
                        
            # 批量保存进数据库
            db.session.commit()
            print(f"✅ [爬虫收工] 本次成功挖到 {new_count} 个新站点，已放入待审核池！")
            
        except Exception as e:
            print(f"❌ [爬虫罢工] 抓取过程中发生错误: {e}")