import os
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings

_RULES = [
    "签到规则：预约时段开始后 15 分钟内可签到，超时未签到系统自动释放座位并记违约。",
    "信用分规则：初始信用分 100 分。低于 60 分者暂停预约权限 7 天。",
    "违约规则：预约成功后未在规定时间内签到、且未主动取消的，记为一次违约，每次扣 5 分信用分。",
    "取消规则：时段开始前 30 分钟以上取消不扣分；30 分钟内取消扣 2 分。",
    "预约上限：每位学生每日最多预约 3 个时段，超出部分系统拒绝。",
    "黑名单规则：连续 3 次违约者直接进入黑名单，暂停预约权限 30 天。",
    "座位状态：座位状态为维修中时不可预约，系统在选座页面置灰显示。",
    "签退规则：使用结束后需主动签退；未签退者按预约时段的结束时间自动签退。",
]

_emb = DashScopeEmbeddings(
    model="text-embedding-v3",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
)

_vs = Chroma.from_texts(texts=_RULES, embedding=_emb)


def retrieve(query, k=3):
    return [(d.page_content, s) for d, s in _vs.similarity_search_with_score(query, k=k)]