import requests
import json
import hashlib
import time
import random
import os
from datetime import datetime
from pathlib import Path

# ================= 全局配置区 =================
# 【核心开关】统一修改所有账号执行的方法
GLOBAL_METHOD = "user.sign"              # 签到方法
# GLOBAL_METHOD = "get.user.item"        # 查询积分

GLOBAL_STYPE = 1

# 【通知配置】企业微信 Webhook 地址
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=906ffb7c-213c-453e-b570-99a01b10bace"

# 【调试开关】
SHOW_RAW_RESPONSE = True

SECRET = "e91270c65422411a9a01b44742865e39"
APPKEY = "76472358"
PLATFORM = "MP-WEIXIN"
FORMAT = "json"
URL = "https://service.milwaukeetool.cn/api/v1/user"

HEADERS = {
    "Host": "service.milwaukeetool.cn",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541739) XWEB/18955",
    "xweb_xhr": "1",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://servicewechat.com/wxc13e77b0a12aac68/59/page-frame.html",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9"
}

# ===========================================

def generate_sign(params_dict):
    sorted_keys = sorted(params_dict.keys())
    s = ""
    for key in sorted_keys:
        val = params_dict[key]
        if isinstance(val, bool):
            val = 1 if val else 0
        s += str(key) + str(val)
    s += SECRET
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def format_sign_status(json_data):
    try:
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        
        if data.get('status') != 200 and data.get('code') != 200:
            return f"❌ 錯誤：API 回應異常"
        
        sign_data = data.get('data', {})
        output = []
        output.append("=" * 50)
        output.append(" Milwaukee 签到结果 ".center(48, "="))
        output.append("=" * 50)
        output.append(f"✅ 当前积分：{sign_data.get('user_score', '未知')}")
        output.append(f"📅 连续签到：{sign_data.get('sign_days', sign_data.get('signcount', '未知'))} 天")
        output.append("=" * 50)
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ 解析错误：{str(e)}"

def send_wechat_notification(failed_accounts, total_count, success_count):
    """发送企业微信通知"""
    if not WEBHOOK_URL or "key=" not in WEBHOOK_URL:
        print("\n⚠️  未配置 Webhook，跳过推送")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fail_details = "\n".join([f"• {name}: {reason}" for name, reason in failed_accounts]) if failed_accounts else "无"

    content = (
        f"🤖 **美沃奇自动签到报告**\n"
        f"📅 时间: {now_str}\n"
        f"--------------------------\n"
        f"✅ 成功: {success_count} 个\n"
        f"❌ 失败: {len(failed_accounts)} 个\n"
        f"📦 总数: {total_count} 个\n"
        f"--------------------------\n"
        f"⚠️ **失败详情:**\n{fail_details}"
    )

    payload = {
        "msgtype": "text",
        "text": { "content": content }
    }

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        if resp.status_code == 200 and resp.json().get("errcode") == 0:
            print("\n📢 企业微信推送成功")
    except:
        print("\n⚠️  推送失败")

def process_account(account_name, index, total, failed_list):
    # 完全使用你原来的环境变量名
    token = os.environ.get("MILWAUKEETOOL_TOKEN_LIST", "")
    client_id = os.environ.get("MILWAUKEETOOL_CLIENT_ID", "")
    token_show = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"

    print(f"\n📌 账号 [{index}/{total}]: {account_name}")
    print(f"      ├─ Token: {token_show}")
    print(f"      └─ ClientID: {client_id}")

    if not token or not client_id:
        msg = "缺少环境变量"
        failed_list.append((account_name, msg))
        return False

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "token": token,
        "client_id": client_id,
        "appkey": APPKEY,
        "format": FORMAT,
        "timestamp": timestamp_str,
        "platform": PLATFORM,
        "method": GLOBAL_METHOD
    }

    payload["sign"] = generate_sign(payload)

    try:
        time.sleep(random.uniform(1,2))
        response = requests.post(URL, headers=HEADERS, json=payload, timeout=10)
        resp_json = response.json()
        code = resp_json.get("code", 0)
        msg = resp_json.get("msg", "") or str(resp_json)

        is_success = code == 200 or "已签到" in msg or "success" in msg.lower()

        if is_success:
            print(f"      ✅ 签到成功 | {msg}")
            # 自动查积分
            time.sleep(1)
            payload_info = payload.copy()
            payload_info["method"] = "get.user.item"
            payload_info["sign"] = generate_sign(payload_info)
            r = requests.post(URL, json=payload_info, headers=HEADERS, timeout=10)
            print(format_sign_status(r.json()))
            return True
        else:
            print(f"      ❌ 失败 | {msg}")
            failed_list.append((account_name, msg[:50]))
            return False

    except Exception as e:
        print(f"      ❌ 异常：{str(e)}")
        failed_list.append((account_name, str(e)))
        return False

def main():
    print("=" * 60)
    print(f"🚀 美沃奇自动签到")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    success = 0
    failed = []
    process_account("默认账号", 1, 1, failed) and success := 1

    print("\n" + "="*60)
    print(f"🏁 完成：成功 {success} 个，失败 {len(failed)} 个")
    print("="*60)

    send_wechat_notification(failed, 1, success)

if __name__ == "__main__":
    main()
