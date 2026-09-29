import os
import requests
import json
from pathlib import Path
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from dotenv import load_dotenv

# 加载环境变量
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

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
    """Legacy adapter: identities and links also come only from the public catalog."""
    from search_catalog import configured_service
    from ai_retrieval import retrieve_recommendations, configured_model
    result = retrieve_recommendations(query, configured_service(), model=configured_model())
    return [{"title": match["site"]["name"], "url": match["site"]["url"], "snippet": match["reason"]}
            for match in result["matches"]]

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
    host = (os.getenv("AI_SERVER_HOST") or "127.0.0.1").strip()
    raw_port = (os.getenv("AI_SERVER_PORT") or "5001").strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise RuntimeError(
            "AI_SERVER_PORT must be an integer between 1 and 65535"
        ) from exc
    if not 1 <= port <= 65535:
        raise RuntimeError(
            "AI_SERVER_PORT must be an integer between 1 and 65535"
        )
    app.run(host=host, port=port)
