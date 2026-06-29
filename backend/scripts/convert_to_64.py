import requests
import base64

# 这里填入你想要转换的网站列表
raw_sites = [
    {"id": 101, "cat": 1, "name": "百度", "url": "https://www.baidu.com", "img": "https://www.baidu.com/favicon.ico"},
    {"id": 102, "cat": 1, "name": "哔哩哔哩", "url": "https://www.bilibili.com", "img": "https://www.bilibili.com/favicon.ico"},
    {"id": 201, "cat": 2, "name": "GitHub", "url": "https://github.com", "img": "https://github.com/favicon.ico"},
    # 你可以在这里继续添加...
]

def to_base64(url):
    try:
        header = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=header, timeout=5)
        if r.status_code == 200:
            b64 = base64.b64encode(r.content).decode('utf-8')
            # 简单判断类型
            mime = "image/x-icon" if "ico" in url else "image/png"
            return f"data:{mime};base64,{b64}"
    except:
        pass
    return "https://via.placeholder.com/50"

print("正在转换中，请稍候...")
final_code = "const websites = ref([\n"

for s in raw_sites:
    b64_data = to_base64(s['img'])
    line = f"  {{ id: {s['id']}, category_id: {s['cat']}, name: '{s['name']}', url: '{s['url']}', logo_url: '{b64_data}' }},\n"
    final_code += line

final_code += "])"

# 将结果保存到文件，因为控制台可能显示不全
with open("result.txt", "w", encoding="utf-8") as f:
    f.write(final_code)

print("✨ 转换完成！请打开同文件夹下的 result.txt，直接复制里面的内容粘贴到 App.vue 即可。")