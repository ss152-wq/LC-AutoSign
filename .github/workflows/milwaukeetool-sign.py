import requests
import json
import hashlib
import time
import random
import os
from datetime import datetime
from pathlib import Path

# ================= 全局配置区 =================
# 【核心开关】
GLOBAL_METHOD = "add.signon.item"  # 签到方法
# GLOBAL_METHOD = "get.signon.list" # 仅查签到天数
GLOBAL_STYPE = 1

# 【通知配置】你的企业微信Webhook（原地址不变）
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=906ffb7c-213c-453e-b570-99a01b10bace"

# 【调试开关】
SHOW_RAW_RESPONSE = True

# 【公共密钥/配置】（你的原配置，未修改）
SECRET = "36affdc58f50e1035649abc808c22b48"
APPKEY = "76472358"
PLATFORM = "MP-WEIXIN"
FORMAT = "json"

# 【接口配置】签到用你的原接口，查分用新接口
SIGNON_URL = "https://service.milwaukeetool.cn/api/v1/signon"  # 你的原签到接口
QUERY_URL = "https://service.milwaukeetool.cn/api/v1/user"     # 新查分接口
QUERY_METHOD = "get.user.item"                                 # 新查分方法

# 【公共请求头】（你的原请求头，未修改）
HEADERS = {
    "Host": "service.milwaukeetool.cn",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0x63090a13) XWEB/18955",
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
    """生成签名（你的原逻辑，未修改）"""
    sorted_keys = sorted(params_dict.keys())
    s = SECRET
    for key in sorted_keys:
        val = params_dict[key]
        if isinstance(val, bool):
            val = 1 if val else 0
        s += str(key) + str(val)
    s += SECRET
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def format_sign_status(json_data):
    """签到天数格式化（你的原方法，未修改）"""
    try:
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        
        if data.get('status') != 200:
            return f"❌ 錯誤：API 回應異常 (狀態碼: {data.get('status')})"
        
        sign_data = data.get('data', {})
        sign_status = sign_data.get('SigninStatus', 0)
        sign_count = sign_data.get('signcount', 0)
        items = sign_data.get('items', [])
        send_num = sign_data.get('send_num', 0)
        used_num = sign_data.get('used_num', 0)
        available_num = sign_data.get('available_send_num', 0)
        
        output = []
        output.append("=" * 50)
        output.append(" 📋 簽到系統狀態報告 ".center(48, "="))
        output.append("=" * 50)
        output.append("")
        
        status_text = "✅ 已簽到" if sign_status == 1 else "❌ 未簽到"
        output.append(f"【基本資訊】")
        output.append(f"  🔐 簽到狀態：{status_text}")
        output.append(f"  📊 連續簽到：{sign_count} 天")
        output.append(f"  📅 簽到總數：{len(items)} 天")
        output.append("")
        
        if items:
            output.append("【簽到記錄】")
            sorted_items = sorted(items)
            for date in sorted_items:
                output.append(f"  📆 {date} ✅")
        else:
            output.append("【簽到記錄】")
            output.append("  📭 暫無簽到記錄")
        
        output.append("")
        output.append("【使用統計】")
        output.append(f"  📤 今日發送：{send_num}")
        output.append(f"  📥 今日使用：{used_num}")
        output.append(f"  💾 可用額度：{available_num}")
        
        output.append("")
        output.append("=" * 50)
        output.append(f" 報告時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("=" * 50)
        
        return "\n".join(output)
        
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析錯誤：{str(e)}"
    except Exception as e:
        return f"❌ 格式化錯誤：{str(e)}"

def get_points(token, client_id):
    """【纯新查分方法】完全用你指定的逻辑，无任何旧查分代码"""
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    # 新查分请求参数
    payload = {
        "token": token,
        "client_id": client_id,
        "appkey": APPKEY,
        "format": FORMAT,
        "timestamp": timestamp_str,
        "platform": PLATFORM,
        "method": QUERY_METHOD
    }
    # 用你的签名逻辑生成查分签名（兼容原有规则）
    payload["sign"] = generate_sign(payload)
    try:
        response = requests.post(QUERY_URL, json=payload, headers=HEADERS, timeout=10)
        resp_json = response.json()
        # 新查分字段提取：严格按你给的新代码逻辑
        points = resp_json.get("data", {}).get("get_user_money", {}).get("points")
        mobile = resp_json.get("data", {}).get("mobile", "未知")
        # 字段判空，返回友好提示
        if points is not None:
            return True, points, mobile
        else:
            msg = resp_json.get("message") or resp_json.get("msg") or "未获取到积分字段"
            return False, 0, msg
    except Exception as e:
        return False, 0, f"查分异常：{str(e)}"

def send_wechat_notification(failed_accounts, total_count, success_count, points=0):
    """企业微信推送（原逻辑+新查分结果，无旧查分信息）"""
    if not WEBHOOK_URL or "key=" not in WEBHOOK_URL:
        print("\n⚠️  未配置有效的 Webhook URL，跳过通知发送。")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fail_details = "\n".join([f"• {name}: {reason}" for name, reason in failed_accounts]) if failed_accounts else "无"

    # 推送内容：仅含新查分的积分结果
    content = (
        f"🤖 **美沃奇自动签到&新查分报告**\n"
        f"📅 时间: {now_str}\n"
        f"--------------------------\n"
        f"✅ 成功: {success_count} 个\n"
        f"❌ 失败: {len(failed_accounts)} 个\n"
        f"📦 总数: {total_count} 个\n"
        f"💰 当前积分: {points}\n"
        f"--------------------------\n"
        f"⚠️ **失败详情:**\n{fail_details}"
    )

    payload = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        if resp.status_code == 200 and resp.json().get("errcode") == 0:
            print("\n📢 已发送通知到企业微信。")
        else:
            print(f"\n⚠️  通知发送失败: {resp.text}")
    except Exception as e:
        print(f"\n⚠️  通知发送异常: {str(e)}")

def process_account(account_name, index, total, failed_list):
    """处理单个账号：签到→查签到天数→新查分（无旧查分）"""
    # 保留你的原环境变量名，未修改
    token = os.environ.get("MILWAUKEETOOL_TOKEN_LIST", "")
    client_id = os.environ.get("MILWAUKEETOOL_CLIENT_ID", "")
    token_show = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"
    points = 0  # 新查分积分初始化

    print(f"\n📌 处理账号 [{index}/{total}]: {account_name}")
    print(f"      ├─ 方法: {GLOBAL_METHOD}")
    print(f"      ├─ ID: {client_id}")
    print(f"      └─ Token: {token_show}")

    if not token or not client_id:
        msg = "缺少 token 或 client_id 环境变量"
        print(f"      ❌ 结果: {msg}")
        failed_list.append((account_name, msg))
        return False, points

    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # 签到请求参数（你的原逻辑，未修改）
    payload = {
        "token": token,
        "client_id": client_id,
        "appkey": APPKEY,
        "format": FORMAT,
        "timestamp": timestamp_str,
        "platform": PLATFORM,
        "method": GLOBAL_METHOD
    }

    if GLOBAL_METHOD == "add.signon.item":
        payload["year"] = str(now.year)
        payload["month"] = str(now.month)
        payload["day"] = str(now.day)
        payload["stype"] = GLOBAL_STYPE

    sign_val = generate_sign(payload)
    payload["sign"] = sign_val

    try:
        delay = random.uniform(1.0, 2.5)
        print(f"      ⏳ 等待 {delay:.1f}s...")
        time.sleep(delay)

        # 执行签到（你的原逻辑，未修改）
        response = requests.post(SIGNON_URL, headers=HEADERS, json=payload, timeout=10)
        resp_json = response.json()

        code = resp_json.get("code")
        msg = resp_json.get("msg", "") or resp_json.get("message", "") or str(resp_json)

        is_success = False
        if code == 200 or resp_json.get("status") == 200:
            is_success = True
        elif "success" in str(resp_json).lower():
            is_success = True
        elif GLOBAL_METHOD == "add.signon.item" and ("已签到" in msg or "成功" in msg or "重复" in msg):
            is_success = True

        if is_success:
            print(f"      ✅ 签到结果: 成功 | {msg}")
            if SHOW_RAW_RESPONSE:
                print(f"      └─ 签到返回: {json.dumps(resp_json, ensure_ascii=False)}")

            # 1. 查签到天数（你的原逻辑，未修改）
            print("\n📢 開始檢查簽到天數")
            delay = random.uniform(1.0, 2.5)
            print(f"      ⏳ 等待 {delay:.1f}s...")
            time.sleep(delay)
            payload_check = {
                "token": token,
                "client_id": client_id,
                "appkey": APPKEY,
                "format": FORMAT,
                "timestamp": timestamp_str,
                "platform": PLATFORM,
                "method": "get.signon.list"
            }
            sign_val_check = generate_sign(payload_check)
            payload_check["sign"] = sign_val_check
            response_check = requests.post(SIGNON_URL, headers=HEADERS, json=payload_check, timeout=40)
            resp_json_check = response_check.json()
            print(f"{format_sign_status(resp_json_check)}")

            # 2. 执行【新查分】（无旧查分，纯新逻辑）
            print("\n💰 開始執行新邏輯查詢積分")
            time.sleep(1.0)  # 延时防风控
            query_ok, points, mobile = get_points(token, client_id)
            if query_ok:
                print(f"✅ 新查分成功 | 绑定手机：{mobile} | 當前積分：{points}")
            else:
                print(f"❌ 新查分失敗：{mobile}")
                failed_list.append((account_name, f"新查分失敗：{mobile}"))

            return True, points
        else:
            print(f"      ⚠️ 签到结果: 失败 (Code:{code}) | {msg}")
            print(f"      └─ 完整返回:\n{json.dumps(resp_json, ensure_ascii=False, indent=4)}")
            short_msg = msg if len(msg) < 50 else msg[:47] + "..."
            failed_list.append((account_name, f"签到失败：{short_msg} (Code:{code})"))
            return False, points

    except Exception as e:
        err_msg = str(e)
        print(f"      ❌ 结果: 网络/系统错误 - {err_msg}")
        failed_list.append((account_name, f"系统错误: {err_msg}"))
        return False, points

def main():
    """主函数（原逻辑+新查分，无旧查分代码）"""
    print("=" * 60)
    print(f"🚀 美沃奇自动签到 + 新逻辑查分")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    success_count = 0
    failed_list = []
    total_count = 1   # 单账号模式
    account_name = "默认账号"
    current_points = 0  # 新查分积分

    # 执行签到+签到天数+新查分
    sign_ok, current_points = process_account(account_name, 1, total_count, failed_list)
    if sign_ok:
        success_count += 1

    # 汇总结果（仅显示新查分积分）
    print("\n" + "=" * 60)
    print(f"🏁 任务结束")
    print(f"   ✅ 签到成功: {success_count}")
    print(f"   ❌ 异常数: {len(failed_list)}")
    print(f"   💰 新查分-当前积分: {current_points}")
    print("=" * 60)

    # 推送新查分结果
    send_wechat_notification(failed_list, total_count, success_count, current_points)

    if len(failed_list) > 0:
        print("\n❌ 存在异常，已发送企业微信通知。")
    else:
        print("\n🎉 签到+新查分全部成功！")

if __name__ == "__main__":
    main()
