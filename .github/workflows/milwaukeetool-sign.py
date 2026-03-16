import requests
import time
import hashlib
import random
import os
from datetime import datetime

# ===================== 配置区（仅需修改此处的 SENDKEY，其他无需改）=====================
GLOBAL_METHOD = "add.signon.item"
GLOBAL_STYPE = 1
SENDKEY = os.getenv("SENDKEY", "")
PUSH_URL = f"https://sctapi.ftqq.com/{SENDKEY}.send" if SENDKEY else ""
SHOW_RAW_RESPONSE = True

# 平台固定参数
SECRET = "36affdc58f50e1035649abc808c22b48"
APPKEY = "76472358"
PLATFORM = "MP-WEIXIN"
FORMAT = "json"
URL = "https://service.milwaukeetool.cn/api/v1/signon"

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://servicewechat.com/wxc13e77b0a12aac68/59/page-frame.html",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "X-Requested-With": "XMLHttpRequest"
}

# ===================== 工具函数 =====================
def generate_sign(params, secret):
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    sign_str = "".join([f"{k}{v}" for k, v in sorted_params]) + secret
    sign = hashlib.md5(sign_str.encode()).hexdigest().upper()
    return sign

def format_sign_status(response_data):
    try:
        status = response_data.get("status", {})
        data = response_data.get("data", {})
        msg = response_data.get("msg", "未知错误")
        
        result = []
        result.append(f"✅ 状态码：{status.get('code', '未知')}")
        result.append(f"📝 提示信息：{msg}")
        
        if data:
            result.append(f"📅 连续签到天数：{data.get('continueDays', 0)}")
            result.append(f"🔢 累计签到次数：{data.get('signCount', 0)}")
            result.append(f"📜 本次签到记录：{data.get('signonRecord', {})}")
            result.append(f"🎁 签到额度：{data.get('signonQuota', 0)}")
        
        return "\n".join(result)
    except Exception as e:
        return f"⚠️ 解析结果失败：{str(e)}\n原始数据：{response_data}"

def send_sendkey_notification(title, content):
    if not SENDKEY or not PUSH_URL:
        print("⚠️ SENDKEY未配置，跳过推送")
        return
    
    try:
        data = {
            "title": title,
            "desp": content
        }
        response = requests.post(PUSH_URL, data=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") == 0:
            print("✅ SENDKEY推送成功")
        else:
            print(f"⚠️ SENDKEY推送失败：{result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 推送通知异常：{str(e)}")

# ===================== 核心业务逻辑 =====================
def process_account(client_id, token, account_name="默认账号"):
    if not client_id or not token:
        error_msg = "❌ 账号信息不完整：Client ID/Token为空"
        print(error_msg)
        return False, error_msg, account_name
    
    try:
        timestamp = str(int(time.time() * 1000))
        params = {
            "method": GLOBAL_METHOD,
            "stype": GLOBAL_STYPE,
            "clientId": client_id,
            "token": token,
            "appKey": APPKEY,
            "platform": PLATFORM,
            "format": FORMAT,
            "timestamp": timestamp
        }
        
        params["sign"] = generate_sign(params, SECRET)
        
        delay = random.uniform(1, 2.5)
        print(f"⏳ 账号 {account_name} 延迟 {delay:.2f} 秒执行...")
        time.sleep(delay)
        
        response = requests.post(URL, data=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        if SHOW_RAW_RESPONSE:
            print(f"📜 账号 {account_name} 原始返回：{response_data}")
        
        status_text = format_sign_status(response_data)
        print(f"\n📌 账号 {account_name} 签到结果：\n{status_text}")
        
        code = response_data.get("status", {}).get("code")
        if code == 0:
            print(f"✅ 账号 {account_name} 签到成功！")
            return True, status_text, account_name
        else:
            error_msg = f"❌ 账号 {account_name} 签到失败：{status_text}"
            return False, error_msg, account_name
    
    except requests.exceptions.RequestException as e:
        error_msg = f"❌ 账号 {account_name} 请求异常：{str(e)}"
        print(error_msg)
        return False, error_msg, account_name
    except Exception as e:
        error_msg = f"❌ 账号 {account_name} 执行异常：{str(e)}"
        print(error_msg)
        return False, error_msg, account_name

def main():
    print("="*50)
    print(f"🚀 milwaukeetool 自动签到启动 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    client_id = os.getenv("MILWAUKEETOOL_CLIENT_ID", "")
    token_list = os.getenv("MILWAUKEETOOL_TOKEN_LIST", "")
    tokens = [t.strip() for t in token_list.split(",") if t.strip()]
    
    if not client_id:
        error_msg = "❌ MILWAUKEETOOL_CLIENT_ID 未配置！"
        print(error_msg)
        send_sendkey_notification("milwaukeetool签到失败", error_msg)
        return
    if not tokens:
        error_msg = "❌ MILWAUKEETOOL_TOKEN_LIST (KEY) 未配置！"
        print(error_msg)
        send_sendkey_notification("milwaukeetool签到失败", error_msg)
        return
    
    failed_list = []
    success_count = 0
    total_count = len(tokens)
    
    for idx, token in enumerate(tokens, 1):
        account_name = f"账号{idx}"
        success, msg, name = process_account(client_id, token, account_name)
        if success:
            success_count += 1
        else:
            failed_list.append((name, msg))
    
    print("\n" + "="*50)
    print(f"📊 签到汇总 | 总数：{total_count} | 成功：{success_count} | 失败：{len(failed_list)}")
    print("="*50)
    
    if failed_list:
        push_title = f"❌ milwaukeetool签到失败 | {len(failed_list)}个账号异常"
        push_content = "### 失败账号详情：\n"
        for name, msg in failed_list:
            push_content += f"- **{name}**：\n{msg}\n\n"
        send_sendkey_notification(push_title, push_content)

if __name__ == "__main__":
    main()
