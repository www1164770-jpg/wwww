import os
import requests
import json
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# ================= 配置缓存 =================
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache', 
    'CACHE_DEFAULT_TIMEOUT': 600
})

# ================= 配置频率限制 =================
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day"],
    storage_uri="memory://"
)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def fetch_deepseek_suggestions(query):
    """调用 DeepSeek API 获取推荐网站"""
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = """
    你是一个专业的互联网网站推荐专家。
    请根据用户的查询，推荐5-10个最相关、最高质量的真实可用网站。
    你必须严格返回一个JSON对象，包含一个名为 "websites" 的数组。绝对不要输出任何其他的解释性文字或Markdown代码块标记。
    JSON格式示例：
    {
      "websites": [
        {
          "title": "网站的名称",
          "url": "https://www.example.com",
          "snippet": "网站的核心功能介绍或推荐理由"
        }
      ]
    }
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"帮我找找这个：{query}"}
        ],
        "response_format": {"type": "json_object"}
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status() 
    
    result_data = response.json()
    content_str = result_data['choices'][0]['message']['content']
    
    try:
        parsed_json = json.loads(content_str)
        return parsed_json.get('websites', [])
    except json.JSONDecodeError:
        print(f"JSON 解析失败: {content_str}")
        return []

def clean_ai_results(items):
    seen_urls = set()
    results = []
    for item in items:
        url = item.get('url', '').strip()
        if not url.startswith('http'): continue
        if url in seen_urls: continue
            
        seen_urls.add(url)
        results.append({
            'title': item.get('title', '未知网站'),
            'url': url,
            'snippet': item.get('snippet', '暂无介绍')
        })
    return results

@app.route('/api/ai/suggest', methods=['GET'])
@limiter.limit("5 per minute")
@cache.cached(query_string=True)
def ai_suggest():
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'code': 400, 'msg': '查询内容不能为空'}), 400
        
    if not DEEPSEEK_API_KEY:
        return jsonify({'code': 500, 'msg': '服务端未配置 DeepSeek 密钥'}), 500

    try:
        raw_items = fetch_deepseek_suggestions(query)
        cleaned_results = clean_ai_results(raw_items)
        return jsonify({'code': 0, 'data': cleaned_results})
        
    except requests.exceptions.RequestException as e:
        print(f"DeepSeek 接口请求异常: {e}")
        return jsonify({'code': 500, 'msg': 'AI大脑暂时短路了，请稍后再试'}), 500
    except Exception as e:
        print(f"服务器内部错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器处理失败'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'code': 429, 'msg': '您思考得太快了，请1分钟后再让AI推荐！'}), 429

if __name__ == '__main__':
    # ✨ 核心修改：将端口改为 5001，避免和 app.py 冲突
    app.run(port=5001)