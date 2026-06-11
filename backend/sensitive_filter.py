"""
敏感词过滤引擎 (基于 DFA 算法)
=================================
使用确定性有限自动机 (Deterministic Finite Automaton) 实现 O(n) 时间复杂度的
敏感词匹配，适合高并发场景下的内容安全审核。

特性：
  - 支持敏感词库动态加载
  - 支持替换中间字符为 *
  - 支持检测（返回 true/false）和过滤（返回替换后文本）两种模式
  - 扩展词库只需向 SENSITIVE_WORDS 集合添加新词

使用方式：
    from sensitive_filter import SensitiveFilter
    sf = SensitiveFilter()
    text = sf.filter("这是一段包含敏感词的文本")  # 替换敏感词
    has_bad = sf.contains("检查是否包含敏感词")    # 仅检测
"""

import re
import os


class DFAFilter:
    """
    基于 DFA 的敏感词过滤器。

    DFA 的核心思想是将敏感词构建为一棵字典树（Trie），
    每个节点代表一个字符，从根到叶子的路径代表一个完整的敏感词。
    匹配时只需遍历一次文本，时间复杂度 O(n)，内存占用可控。
    """

    def __init__(self):
        self._root = {}  # DFA 根节点：dict of char -> dict
        self._built = False

    def _build(self, words):
        """
        根据敏感词列表构建 DFA 字典树。

        参数：
            words: 敏感词列表/集合
        """
        self._root = {}
        for word in words:
            node = self._root
            for ch in word:
                if ch not in node:
                    node[ch] = {}
                node = node[ch]
            node['__END__'] = True  # 标记词尾
        self._built = True

    def _filter_char(self, ch):
        """过滤特殊字符，忽略空格和标点符号的干扰"""
        if ch in ' \t\n\r\v,./?;:\'"[]{}!@#$%^&*()-_=+~`|\\':
            return None
        return ch.lower()  # 统一小写，实现大小写不敏感

    def contains(self, text):
        """
        检测文本是否包含敏感词。

        参数：
            text (str): 待检测文本

        返回：
            bool: 包含敏感词返回 True，否则返回 False
        """
        if not self._built or not text:
            return False

        text_len = len(text)
        i = 0
        while i < text_len:
            node = self._root
            j = i
            while j < text_len and text[j].lower() in node:
                node = node[text[j].lower()]
                if '__END__' in node:
                    return True
                j += 1
            i += 1
        return False

    def filter(self, text, replace_char='*'):
        """
        过滤文本中的敏感词，将敏感词中间字符替换为 replace_char。

        参数：
            text (str): 待过滤文本
            replace_char (str): 替换字符，默认 '*'

        返回：
            str: 过滤后的文本
            list: 命中的敏感词列表
        """
        if not self._built or not text:
            return text, []

        result = list(text)
        matched_words = []
        text_len = len(text)
        i = 0

        while i < text_len:
            node = self._root
            j = i
            match_end = -1
            while j < text_len and text[j].lower() in node:
                node = node[text[j].lower()]
                if '__END__' in node:
                    match_end = j
                j += 1

            if match_end >= 0:
                # 找到了敏感词，记录并替换
                word = text[i:match_end + 1]
                matched_words.append(word)
                # 保留首尾字符，中间替换为 *
                if match_end - i + 1 > 2:
                    for k in range(i + 1, match_end):
                        result[k] = replace_char
                elif match_end - i + 1 == 2:
                    result[i + 1] = replace_char
                i = match_end + 1
            else:
                i += 1

        return ''.join(result), matched_words

    def find_all(self, text):
        """
        找出文本中所有敏感词。

        参数：
            text (str): 待检测文本

        返回：
            list: 所有命中的敏感词列表
        """
        if not self._built or not text:
            return []

        matched = []
        text_len = len(text)
        i = 0

        while i < text_len:
            node = self._root
            j = i
            match_end = -1
            while j < text_len and text[j].lower() in node:
                node = node[text[j].lower()]
                if '__END__' in node:
                    match_end = j
                j += 1

            if match_end >= 0:
                matched.append(text[i:match_end + 1])
                i = match_end + 1
            else:
                i += 1

        return matched


# ==================== 内置敏感词库 ====================
# 注意：这是一个示例词库，生产环境应接入专业内容安全 API（如阿里云/腾讯云内容安全）
DEFAULT_SENSITIVE_WORDS = {
    # 政治敏感类
    "falungong", "法轮功", "法轮大法",
    # 暴恐类
    "恐怖袭击", "自制炸药", "制作炸弹",
    # 色情低俗类
    "色情", "淫秽", "成人影片", "av女优", "黄片",
    # 赌博类
    "赌博网站", "赌场", "博彩平台", "六合彩",
    # 毒品类
    "毒品", "吸毒", "海洛因", "冰毒", "大麻",
    # 辱骂攻击类
    "傻逼", "sb", "操你", "fuck you", "他妈的", "狗日的",
    # 诈骗类
    "代办信用卡", "无抵押贷款", "刷单兼职", "中奖信息",
}

# ==================== 全局单例 ====================
_global_filter = None


def get_filter():
    """
    获取全局敏感词过滤器实例（单例模式）。
    首次调用时自动构建 DFA 字典树。
    """
    global _global_filter
    if _global_filter is None:
        _global_filter = DFAFilter()
        # 尝试从外部文件加载词库
        words = set(DEFAULT_SENSITIVE_WORDS)
        word_file = os.path.join(os.path.dirname(__file__), 'sensitive_words.txt')
        if os.path.exists(word_file):
            with open(word_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        words.add(line.lower())
        _global_filter._build(words)
    return _global_filter


# ==================== 便捷函数 ====================

def check_content(text):
    """
    检查文本内容是否合规。

    参数：
        text (str): 待检测文本（文章标题、正文、评论等）

    返回：
        dict: {
            'safe': bool,          # 是否安全（不含敏感词）
            'filtered_text': str,  # 过滤后的文本（敏感词已被替换）
            'hit_words': list,     # 命中的敏感词列表
        }
    """
    if not text:
        return {'safe': True, 'filtered_text': '', 'hit_words': []}

    sf = get_filter()
    filtered_text, hit_words = sf.filter(text)
    return {
        'safe': len(hit_words) == 0,
        'filtered_text': filtered_text,
        'hit_words': hit_words
    }


def is_safe(text):
    """快速判断文本是否安全（不包含任何敏感词）"""
    if not text:
        return True
    return get_filter().contains(text) is False
