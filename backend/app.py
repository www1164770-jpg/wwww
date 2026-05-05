import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
import requests
import time
from models import db, User, Category, Website, ClickLog
from sqlalchemy import func
from datetime import datetime, timedelta
import json

# ✨ 关键点：启动时加载 .env 文件中的机密信息
load_dotenv()

app = Flask(__name__)
# 允许跨域请求
CORS(app)

# 配置数据库连接 URL (MySQL)
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?charset=utf8mb4"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ================= 示例路由：获取所有导航数据 =================
# backend/app.py

@app.route('/api/nav-data', methods=['GET'])
def get_nav_data():
    try:
        # 1. 查询所有分类，按 sort_order 排序
        categories = Category.query.order_by(Category.sort_order).all()
        
        # 2. 组装成前端需要的嵌套格式
        result = []
        for cat in categories:
            result.append({
                "id": cat.id,
                "name": cat.name,
                "profession_type": cat.profession_type,
                "sites": [{
                    "id": site.id,
                    "category_id": site.category_id,
                    "name": site.name,
                    "url": site.url,
                    "logo_url": site.logo_url,
                    "clicks": site.clicks
                } for site in cat.websites]
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= 1. 模拟数据库 (保持不变) =================
categories_db = [
    {"id": 1, "name": "常用推荐"},
    {"id": 2, "name": "开发社区"},
    {"id": 3, "name": "摸鱼娱乐"},
    {"id": 4, "name": "实用工具"},
    {"id": 5, "name": "AI 神器"}
]

websites_db = [
    # ===== 分类 1：常用推荐 =====
    {"id": 101, "category_id": 1, "name": "哔哩哔哩", "url": "https://www.bilibili.com", "logo_url": "", "clicks": 1250},
    {"id": 102, "category_id": 1, "name": "知乎", "url": "https://www.zhihu.com", "logo_url": "", "clicks": 856},
    {"id": 103, "category_id": 1, "name": "微博", "url": "https://weibo.com", "logo_url": "", "clicks": 720},
    {"id": 104, "category_id": 1, "name": "淘宝", "url": "https://www.taobao.com", "logo_url": "", "clicks": 1100},
    {"id": 105, "category_id": 1, "name": "京东", "url": "https://www.jd.com", "logo_url": "", "clicks": 980},
    {"id": 106, "category_id": 1, "name": "百度", "url": "https://www.baidu.com", "logo_url": "", "clicks": 2000},
    {"id": 107, "category_id": 1, "name": "腾讯视频", "url": "https://v.qq.com", "logo_url": "", "clicks": 650},
    {"id": 108, "category_id": 1, "name": "爱奇艺", "url": "https://www.iqiyi.com", "logo_url": "", "clicks": 600},
    {"id": 109, "category_id": 1, "name": "优酷", "url": "https://www.youku.com", "logo_url": "", "clicks": 480},
    {"id": 110, "category_id": 1, "name": "网易云音乐", "url": "https://music.163.com", "logo_url": "", "clicks": 870},
    {"id": 111, "category_id": 1, "name": "QQ音乐", "url": "https://y.qq.com", "logo_url": "", "clicks": 760},
    {"id": 112, "category_id": 1, "name": "天猫", "url": "https://www.tmall.com", "logo_url": "", "clicks": 890},
    {"id": 113, "category_id": 1, "name": "拼多多", "url": "https://www.pinduoduo.com", "logo_url": "", "clicks": 950},
    {"id": 114, "category_id": 1, "name": "12306", "url": "https://www.12306.cn", "logo_url": "", "clicks": 430},
    {"id": 115, "category_id": 1, "name": "高德地图", "url": "https://www.amap.com", "logo_url": "", "clicks": 560},

    # ===== 分类 2：开发社区 =====
    {"id": 201, "category_id": 2, "name": "GitHub", "url": "https://github.com", "logo_url": "", "clicks": 980},
    {"id": 202, "category_id": 2, "name": "GitLab", "url": "https://gitlab.com", "logo_url": "", "clicks": 420},
    {"id": 203, "category_id": 2, "name": "Gitee", "url": "https://gitee.com", "logo_url": "", "clicks": 380},
    {"id": 204, "category_id": 2, "name": "掘金", "url": "https://juejin.cn", "logo_url": "", "clicks": 430},
    {"id": 205, "category_id": 2, "name": "CSDN", "url": "https://www.csdn.net", "logo_url": "", "clicks": 560},
    {"id": 206, "category_id": 2, "name": "博客园", "url": "https://www.cnblogs.com", "logo_url": "", "clicks": 310},
    {"id": 207, "category_id": 2, "name": "Stack Overflow", "url": "https://stackoverflow.com", "logo_url": "", "clicks": 670},
    {"id": 208, "category_id": 2, "name": "MDN Web Docs", "url": "https://developer.mozilla.org", "logo_url": "", "clicks": 590},
    {"id": 209, "category_id": 2, "name": "npm", "url": "https://www.npmjs.com", "logo_url": "", "clicks": 480},
    {"id": 210, "category_id": 2, "name": "Docker Hub", "url": "https://hub.docker.com", "logo_url": "", "clicks": 350},
    {"id": 211, "category_id": 2, "name": "LeetCode", "url": "https://leetcode.cn", "logo_url": "", "clicks": 720},
    {"id": 212, "category_id": 2, "name": "牛客网", "url": "https://www.nowcoder.com", "logo_url": "", "clicks": 540},
    {"id": 213, "category_id": 2, "name": "V2EX", "url": "https://www.v2ex.com", "logo_url": "", "clicks": 390},
    {"id": 214, "category_id": 2, "name": "SegmentFault", "url": "https://segmentfault.com", "logo_url": "", "clicks": 280},
    {"id": 215, "category_id": 2, "name": "Vercel", "url": "https://vercel.com", "logo_url": "", "clicks": 460},

    # ===== 分类 3：摸鱼娱乐 =====
    {"id": 301, "category_id": 3, "name": "抖音", "url": "https://www.douyin.com", "logo_url": "", "clicks": 520},
    {"id": 302, "category_id": 3, "name": "小红书", "url": "https://www.xiaohongshu.com", "logo_url": "", "clicks": 480},
    {"id": 303, "category_id": 3, "name": "微信读书", "url": "https://weread.qq.com", "logo_url": "", "clicks": 320},
    {"id": 304, "category_id": 3, "name": "豆瓣", "url": "https://www.douban.com", "logo_url": "", "clicks": 410},
    {"id": 305, "category_id": 3, "name": "虎扑", "url": "https://www.hupu.com", "logo_url": "", "clicks": 290},
    {"id": 306, "category_id": 3, "name": "NGA玩家社区", "url": "https://nga.178.com", "logo_url": "", "clicks": 260},
    {"id": 307, "category_id": 3, "name": "Steam", "url": "https://store.steampowered.com", "logo_url": "", "clicks": 680},
    {"id": 308, "category_id": 3, "name": "Epic Games", "url": "https://www.epicgames.com", "logo_url": "", "clicks": 350},
    {"id": 309, "category_id": 3, "name": "网易游戏", "url": "https://game.163.com", "logo_url": "", "clicks": 420},
    {"id": 310, "category_id": 3, "name": "腾讯游戏", "url": "https://game.qq.com", "logo_url": "", "clicks": 510},
    {"id": 311, "category_id": 3, "name": "漫画柜", "url": "https://www.manhuagui.com", "logo_url": "", "clicks": 230},
    {"id": 312, "category_id": 3, "name": "哔哩哔哩漫画", "url": "https://manga.bilibili.com", "logo_url": "", "clicks": 280},
    {"id": 313, "category_id": 3, "name": "网易新闻", "url": "https://news.163.com", "logo_url": "", "clicks": 370},
    {"id": 314, "category_id": 3, "name": "今日头条", "url": "https://www.toutiao.com", "logo_url": "", "clicks": 440},
    {"id": 315, "category_id": 3, "name": "虎嗅", "url": "https://www.huxiu.com", "logo_url": "", "clicks": 310},

    # ===== 分类 4：实用工具 =====
    {"id": 401, "category_id": 4, "name": "ProcessOn", "url": "https://www.processon.com", "logo_url": "", "clicks": 380},
    {"id": 402, "category_id": 4, "name": "Excalidraw", "url": "https://excalidraw.com", "logo_url": "", "clicks": 290},
    {"id": 403, "category_id": 4, "name": "TinyPNG", "url": "https://tinypng.com", "logo_url": "", "clicks": 450},
    {"id": 404, "category_id": 4, "name": "Squoosh", "url": "https://squoosh.app", "logo_url": "", "clicks": 220},
    {"id": 405, "category_id": 4, "name": "Carbon", "url": "https://carbon.now.sh", "logo_url": "", "clicks": 310},
    {"id": 406, "category_id": 4, "name": "Regex101", "url": "https://regex101.com", "logo_url": "", "clicks": 340},
    {"id": 407, "category_id": 4, "name": "JSON格式化", "url": "https://jsonformatter.curiousconcept.com", "logo_url": "", "clicks": 280},
    {"id": 408, "category_id": 4, "name": "Can I Use", "url": "https://caniuse.com", "logo_url": "", "clicks": 390},
    {"id": 409, "category_id": 4, "name": "Notion", "url": "https://www.notion.so", "logo_url": "", "clicks": 620},
    {"id": 410, "category_id": 4, "name": "飞书", "url": "https://www.feishu.cn", "logo_url": "", "clicks": 540},
    {"id": 411, "category_id": 4, "name": "腾讯文档", "url": "https://docs.qq.com", "logo_url": "", "clicks": 480},
    {"id": 412, "category_id": 4, "name": "石墨文档", "url": "https://shimo.im", "logo_url": "", "clicks": 320},
    {"id": 413, "category_id": 4, "name": "百度翻译", "url": "https://fanyi.baidu.com", "logo_url": "", "clicks": 560},
    {"id": 414, "category_id": 4, "name": "DeepL翻译", "url": "https://www.deepl.com", "logo_url": "", "clicks": 490},
    {"id": 415, "category_id": 4, "name": "Cloudflare", "url": "https://www.cloudflare.com", "logo_url": "", "clicks": 270},
    {"id": 416, "category_id": 4, "name": "iLovePDF", "url": "https://www.ilovepdf.com", "logo_url": "", "clicks": 350},
    {"id": 417, "category_id": 4, "name": "Convertio", "url": "https://convertio.co", "logo_url": "", "clicks": 300},
    {"id": 418, "category_id": 4, "name": "Unsplash", "url": "https://unsplash.com", "logo_url": "", "clicks": 410},

    # ===== 分类 5：AI 神器 =====
    {"id": 501, "category_id": 5, "name": "ChatGPT", "url": "https://chat.openai.com", "logo_url": "", "clicks": 760},
    {"id": 502, "category_id": 5, "name": "Claude", "url": "https://claude.ai", "logo_url": "", "clicks": 580},
    {"id": 503, "category_id": 5, "name": "Gemini", "url": "https://gemini.google.com", "logo_url": "", "clicks": 490},
    {"id": 504, "category_id": 5, "name": "文心一言", "url": "https://yiyan.baidu.com", "logo_url": "", "clicks": 420},
    {"id": 505, "category_id": 5, "name": "通义千问", "url": "https://tongyi.aliyun.com", "logo_url": "", "clicks": 380},
    {"id": 506, "category_id": 5, "name": "讯飞星火", "url": "https://xinghuo.xfyun.cn", "logo_url": "", "clicks": 310},
    {"id": 507, "category_id": 5, "name": "Kimi", "url": "https://kimi.moonshot.cn", "logo_url": "", "clicks": 450},
    {"id": 508, "category_id": 5, "name": "豆包", "url": "https://www.doubao.com", "logo_url": "", "clicks": 390},
    {"id": 509, "category_id": 5, "name": "Midjourney", "url": "https://www.midjourney.com", "logo_url": "", "clicks": 520},
    {"id": 510, "category_id": 5, "name": "Stable Diffusion", "url": "https://stability.ai", "logo_url": "", "clicks": 340},
    {"id": 511, "category_id": 5, "name": "Runway", "url": "https://runwayml.com", "logo_url": "", "clicks": 280},
    {"id": 512, "category_id": 5, "name": "Suno AI", "url": "https://suno.ai", "logo_url": "", "clicks": 360},
    {"id": 513, "category_id": 5, "name": "GitHub Copilot", "url": "https://github.com/features/copilot", "logo_url": "", "clicks": 470},
    {"id": 514, "category_id": 5, "name": "Cursor", "url": "https://www.cursor.com", "logo_url": "", "clicks": 530},
    {"id": 515, "category_id": 5, "name": "Perplexity", "url": "https://www.perplexity.ai", "logo_url": "", "clicks": 410},
    {"id": 516, "category_id": 5, "name": "Hugging Face", "url": "https://huggingface.co", "logo_url": "", "clicks": 350},
    {"id": 517, "category_id": 5, "name": "DeepSeek", "url": "https://www.deepseek.com", "logo_url": "", "clicks": 620},
    {"id": 518, "category_id": 5, "name": "智谱清言", "url": "https://chatglm.cn", "logo_url": "", "clicks": 290},
]

# ================= 2. 基础 API 路由 (保持不变) =================

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({"categories": categories_db, "websites": websites_db})

# backend/app.py

# ✨ 1. 在路由上方定义好“全网基础热度大字典”
# ✨ 1. 全网基础热度（保持不变）
BASE_HOTNESS = {
    # 常用推荐
    "百度": 200000, "哔哩哔哩": 50000, "知乎": 30000, "微博": 45000,
    "淘宝": 80000, "京东": 70000, "腾讯视频": 35000, "爱奇艺": 32000,
    "优酷": 20000, "网易云音乐": 40000, "QQ音乐": 38000, "天猫": 65000,
    "拼多多": 55000, "12306": 18000, "高德地图": 22000,
    # 开发社区
    "GitHub": 25000, "GitLab": 8000, "Gitee": 7000, "掘金": 10000,
    "CSDN": 15000, "博客园": 6000, "Stack Overflow": 18000, "MDN Web Docs": 12000,
    "npm": 9000, "Docker Hub": 7500, "LeetCode": 20000, "牛客网": 14000,
    "V2EX": 8500, "SegmentFault": 5000, "Vercel": 9500,
    # 摸鱼娱乐
    "抖音": 80000, "小红书": 42000, "微信读书": 15000, "豆瓣": 18000,
    "虎扑": 12000, "NGA玩家社区": 10000, "Steam": 28000, "Epic Games": 14000,
    "网易游戏": 17000, "腾讯游戏": 22000, "漫画柜": 8000, "哔哩哔哩漫画": 9000,
    "网易新闻": 16000, "今日头条": 35000, "虎嗅": 11000,
    # 实用工具
    "Notion": 25000, "飞书": 20000, "腾讯文档": 18000, "石墨文档": 10000,
    "百度翻译": 22000, "DeepL翻译": 19000, "TinyPNG": 12000, "Can I Use": 9000,
    "Regex101": 8000, "Carbon": 7000, "ProcessOn": 11000, "Unsplash": 13000,
    # AI 神器
    "ChatGPT": 60000, "Claude": 35000, "Gemini": 28000, "文心一言": 20000,
    "通义千问": 18000, "讯飞星火": 14000, "Kimi": 22000, "豆包": 19000,
    "Midjourney": 26000, "DeepSeek": 30000, "GitHub Copilot": 21000,
    "Cursor": 24000, "Perplexity": 16000, "Hugging Face": 13000,
    "Suno AI": 12000, "Runway": 10000, "智谱清言": 9000, "Stable Diffusion": 11000,
}

# ===== 热度缓存：存储上一次抓取的各网站热度，用于计算涨跌率 =====
_hotness_cache = {}
_hotness_cache_time = {}


def fetch_online_hotness():
    """从多个公开热榜 API 抓取实时热度，返回 {网站名: 热度分数}"""
    hotness = {}
    hdrs = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
    }
    # 源1：微博实时热搜
    try:
        r = requests.get('https://weibo.com/ajax/side/hotSearch',
            headers={**hdrs, 'Referer': 'https://weibo.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('realtime', [])
            hotness['微博'] = sum(int(x.get('num', 0)) for x in items[:50])
    except Exception:
        pass
    # 源2：知乎热榜
    try:
        r = requests.get('https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50',
            headers={**hdrs, 'Referer': 'https://www.zhihu.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', [])
            total = 0
            for item in items:
                raw = item.get('detail_text', '0').replace('万热度', '').replace('万', '')
                try:
                    total += int(float(raw) * 10000)
                except Exception:
                    total += 5000
            hotness['知乎'] = total
    except Exception:
        pass
    # 源3：百度实时热搜
    try:
        r = requests.get('https://top.baidu.com/api/board?platform=wise&tab=realtime',
            headers={**hdrs, 'Referer': 'https://top.baidu.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('cards', [{}])[0].get('content', [])
            hotness['百度'] = sum(int(x.get('hotScore', 0)) for x in items[:30])
    except Exception:
        pass
    # 源4：今日头条热榜
    try:
        r = requests.get('https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc',
            headers={**hdrs, 'Referer': 'https://www.toutiao.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', [])
            hotness['今日头条'] = sum(int(x.get('HotValue', 0)) for x in items[:30])
    except Exception:
        pass
    # 源5：GitHub Trending 今日 Star 增量
    try:
        r = requests.get('https://api.gitterapp.com/repositories?since=daily',
            headers=hdrs, timeout=6)
        if r.status_code == 200:
            repos = r.json()
            hotness['GitHub'] = sum(int(x.get('stars', 0)) for x in repos[:25]) * 10
    except Exception:
        pass
    # 源6：哔哩哔哩热门视频播放量
    try:
        r = requests.get('https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all',
            headers={**hdrs, 'Referer': 'https://www.bilibili.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('list', [])
            hotness['哔哩哔哩'] = sum(int(x.get('stat', {}).get('view', 0)) for x in items[:20])
    except Exception:
        pass
    # 源7：抖音热榜
    try:
        r = requests.get('https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/',
            headers={**hdrs, 'Referer': 'https://www.douyin.com'}, timeout=6)
        if r.status_code == 200:
            items = r.json().get('word_list', [])
            hotness['抖音'] = sum(int(x.get('hot_value', 0)) for x in items[:30])
    except Exception:
        pass
    return hotness

# ================= 1. 上传/更新配置到云端 =================
@app.route('/api/user/sync', methods=['POST'])
def sync_user_settings():
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"error": "未登录"}), 401

    # 查找用户，如果没有就顺手创建一个（兼容你目前的手机号模拟登录逻辑）
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)

    # 同步各项配置
    if 'dark_mode' in data:
        user.dark_mode = data['dark_mode']
    if 'custom_wallpaper' in data:
        user.custom_wallpaper = data['custom_wallpaper']
    if 'current_engine' in data:
        user.current_engine = data['current_engine']
    if 'selected_engines' in data:
        user.selected_engines = json.dumps(data['selected_engines']) # 列表转为字符串存储
    if 'avatar_url' in data:
        user.avatar_url = data['avatar_url']

    db.session.commit()
    return jsonify({"success": True, "message": "配置已同步到云端 ☁️"})

# ================= 2. 登录时拉取云端配置 =================
@app.route('/api/user/settings', methods=['GET'])
def get_user_settings():
    username = request.args.get('username')
    
    if not username:
        return jsonify({"error": "缺少用户名"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "找不到用户"}), 404

    return jsonify({
        "dark_mode": user.dark_mode,
        "custom_wallpaper": user.custom_wallpaper,
        "current_engine": user.current_engine,
        "selected_engines": json.loads(user.selected_engines) if user.selected_engines else None,
        "avatar_url": user.avatar_url
    })

@app.route('/api/ranking', methods=['GET'])
def get_ranking():
    global _hotness_cache, _hotness_cache_time
    try:
        current = fetch_online_hotness()
        ranking_data = []
        all_sites_db = Website.query.all()
        for site in all_sites_db:
            name = site.name
            cur_score = current.get(name, 0)
            last_score = _hotness_cache.get(name, 0)
            if last_score > 0 and cur_score > 0:
                rate = round((cur_score - last_score) / last_score * 100, 1)
            elif cur_score > 0 and last_score == 0:
                rate = 100.0
            else:
                rate = 0.0
            delta = cur_score - last_score
            base = BASE_HOTNESS.get(name, 0)
            sort_score = cur_score + base // 100
            ranking_data.append({
                'id': site.id,
                'name': name,
                'url': site.url,
                'clicks': cur_score,
                'delta': delta,
                'growth_rate': rate,
                'sort_score': sort_score,
            })
        for name, score in current.items():
            _hotness_cache[name] = score
            _hotness_cache_time[name] = time.time()
        ranking_data.sort(key=lambda x: (abs(x['growth_rate']), x['sort_score']), reverse=True)
        return jsonify(ranking_data[:10])
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
@app.route('/api/click', methods=['POST'])
def record_click():
    data = request.json
    site_id = data.get('id')
    
    if not site_id:
        return jsonify({"error": "缺少网站ID"}), 400
        
    site = Website.query.get(site_id)
    if site:
        # 1. 历史总点击量依然累加
        site.clicks += 1  
        
        # 2. ✨ 新增：生成一条带有时间戳的“热搜流水”记录
        new_log = ClickLog(website_id=site.id)
        db.session.add(new_log)
        
        db.session.commit()
        return jsonify({"success": True, "new_clicks": site.clicks})
    
    return jsonify({"error": "找不到该网站"}), 404

@app.route('/api/cache_logo', methods=['POST'])
def cache_logo():
    data = request.json
    site_id = data.get('id')
    url = data.get('url')
    if url:
        domain = url.split('//')[-1].split('/')[0].replace('www.', '')
        logo_url = f"https://www.google.com/s2/favicons?sz=128&domain={domain}"
        for site in websites_db:
            if site['id'] == site_id:
                site['logo_url'] = logo_url
                break
        return jsonify({"status": "success", "logo_url": logo_url})
    return jsonify({"status": "error", "message": "无效的 URL"})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    time.sleep(1) 
    reply = "收到！但我现在还是个模拟数据。你可以试着在输入框里包含“设计”、“摸鱼”或“代码”等关键词。"
    if "设计" in user_message:
        reply = "找设计灵感吗？强烈推荐你去看看 Dribbble、Behance 或者站酷！"
    elif "摸鱼" in user_message or "游戏" in user_message:
        reply = "偷偷告诉你，工作累了可以去刷刷 B站 或者 抖音 放松一下~"
    elif "代码" in user_message or "开发" in user_message or "前端" in user_message:
        reply = "推荐多看 GitHub 的开源项目，遇到 Bug 直接上 StackOverflow 搜！"
    return jsonify({"reply": reply})

# ================= 3. GitHub 回调 (✨ 安全升级版) =================
@app.route('/api/github/callback', methods=['GET'])
def github_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "缺少授权码 (code)"}), 400

    # ✨ 从系统的环境变量中安全读取，取代原来的明文密码
    CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

    if not CLIENT_ID or not CLIENT_SECRET:
        return jsonify({"error": "服务器未配置 GitHub 密钥，请检查 .env 文件！"}), 500

    # 用 code 换取 Access Token
    token_response = requests.post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code
        },
        headers={'Accept': 'application/json'}
    )
    
    token_json = token_response.json()
    access_token = token_json.get('access_token')

    if not access_token:
         return jsonify({"error": "获取 Access Token 失败", "details": token_json}), 400

    # 获取用户信息
    user_response = requests.get(
        'https://api.github.com/user',
        headers={'Authorization': f'token {access_token}'}
    )
    user_data = user_response.json()

    username = user_data.get('login', 'GitHub用户')
    avatar = user_data.get('avatar_url', '')

    frontend_url = f"http://localhost:5173/?login=success&username={username}&avatar={avatar}"
    print(f"🎉 GitHub 登录成功！用户: {username}")
    return redirect(frontend_url)

if __name__ == '__main__':
    with app.app_context():
        # 启动时自动同步所有分类和网站到数据库
        try:
            from init_db import all_categories, all_sites, get_logo_url
            import pymysql

            env_db = {
                'host': os.getenv('DB_HOST', '127.0.0.1'),
                'user': os.getenv('DB_USER', 'root'),
                'password': os.getenv('DB_PASSWORD', ''),
                'database': os.getenv('DB_NAME', 'nav_site'),
                'charset': 'utf8mb4'
            }
            conn = pymysql.connect(**env_db)
            cur = conn.cursor()

            # 同步分类
            for cat in all_categories:
                cat_id, profession, name, sort = cat
                cur.execute(
                    "INSERT INTO categories (id,name,profession_type,sort_order) VALUES (%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE name=%s, profession_type=%s, sort_order=%s",
                    (cat_id, name, profession, sort, name, profession, sort)
                )

            # 同步网站（跳过已存在的）
            new_count = 0
            for site in all_sites:
                cur.execute("SELECT id FROM websites WHERE name=%s AND category_id=%s",
                            (site['name'], site['cat']))
                if not cur.fetchone():
                    logo = get_logo_url(site['url'])
                    cur.execute(
                        "INSERT INTO websites (category_id,name,url,logo_url) VALUES (%s,%s,%s,%s)",
                        (site['cat'], site['name'], site['url'], logo)
                    )
                    new_count += 1

            conn.commit()
            conn.close()
            if new_count > 0:
                print(f"✅ 启动同步：新增 {new_count} 个网站")
            else:
                print(f"✅ 数据库已是最新，共 {len(all_sites)} 条网站数据")
        except Exception as e:
            print(f"⚠️  启动同步失败（不影响运行）: {e}")

    print("🚀 智汇导航后端服务已启动！正在监听 http://127.0.0.1:5000 ...")
    app.run(host='0.0.0.0', port=5000, debug=True)