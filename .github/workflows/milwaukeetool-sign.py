import requests
import time
import hashlib
import random
import os
from datetime import datetime

# ===================== 配置区（仅需修改此处）=====================
# 核心开关：add.signon.item = 签到，get.signon.list = 查询签到列表
GLOBAL_METHOD = "add.signon.item"
GLOBAL_STYPE = 1  # 签到类型，固定值

# 推送配置：Server酱 SENDKEY（替换为你的实际 SENDKEY，空则关闭推送）
SENDKEY = os.getenv("SENDKEY", "")
# 推送接口（Server酱 Turbo 版，无需修改）
PUSH_URL = f"https://sctapi.ftqq.com/{SENDKEY}.send" if SENDKEY else ""

# 调试开关：开启后打印完整请求参数和返回（排查500必备）
SHOW_DETAIL_LOG = True
# 重试配置：失败后重试次数/间隔（应对临时500）
RETRY_TIMES = 1
RETRY_DELAY = 60  # 重试间隔（秒）
# 随机延迟：增大延迟避免风控（3-8秒）
MIN_DELAY = 3
MAX_DELAY = 8

# 平台固定参数（需和抓包一致，若抓包不同则替换）
SECRET = "36affdc58f50e1035649abc808c22b48"
APPKEY = "76472358"
PLATFORM = "MP-WEIXIN"
FORMAT = "json"
URL = "https://service.milwaukeetool.cn/api/v1/signon"

# 请求头（模拟微信小程序真实环境，降低风控）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.61(0x18003d29) NetType/WIFI Language/zh_CN",
    "Referer": "https://servicewechat.com/wxc13e77b0a12aac68/59/page-frame.html",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "close"  # 关闭长连接，避免服务器连接数超限
}

# ===================== 工具函数 =====================
def generate_sign(params, secret):
    """生成API请求签名（核心：参数排序+MD5加密）"""
    try:
        # 按参数名升序排序（必须和服务器验签逻辑一致）
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        # 拼接参数字符串
        sign_str = "".join([f"{k}{v}" for k, v in sorted_params]) + secret
        # MD5加密并转大写
        sign = hashlib.md5(sign_str.encode()).hexdigest().upper()
        if SHOW_DETAIL_LOG:
            print(f"🔑 签名原始串：{sign_str} | 生成签名：{sign}")
        return sign
    except Exception as e:
        print(f"❌ 生成签名失败：{str(e)}")
        return ""

def format_sign_status(response_data):
    """格式化签到返回结果"""
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
    """通过SENDKEY推送通知"""
    if not SENDKEY or not PUSH_URL:
        print("⚠️ SENDKEY未配置，跳过推送")
        return
    
    try:
        data = {
            "title": title,
            "desp": content  # 支持Markdown格式
        }
        # 超时时间加长，避免推送失败
        response = requests.post(PUSH_URL, data=data, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") == 0:
            print("✅ SENDKEY推送成功")
        else:
            print(f"⚠️ SENDKEY推送失败：{result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 推送通知异常：{str(e)}")

# ===================== 核心业务逻辑（含重试）=====================
def process_account(client_id, token, account_name="默认账号"):
    """处理单个账号的签到逻辑（含重试）"""
    if not client_id or not token:
        error_msg = "❌ 账号信息不完整：Client ID/Token为空"
        print(error_msg)
        return False, error_msg, account_name
    
    # 重试逻辑
    for attempt in range(RETRY_TIMES + 1):
        try:
            # 1. 构造请求参数
            timestamp = str(int(time.time() * 1000))  # 毫秒时间戳（必须）
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
            
            # 2. 生成签名
            sign = generate_sign(params, SECRET)
            if not sign:
                raise Exception("签名生成失败")
            params["sign"] = sign
            
            # 3. 打印详细请求参数（排查500用）
            if SHOW_DETAIL_LOG:
                print(f"\n📋 账号 {account_name} 第 {attempt+1} 次请求参数：")
                for k, v in params.items():
                    print(f"  {k}: {v}")
            
            # 4. 随机延迟（模拟人工操作，避免风控）
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            print(f"⏳ 账号 {account_name} 第 {attempt+1} 次延迟 {delay:.2f} 秒执行...")
            time.sleep(delay)
            
            # 5. 发送签到请求（关闭重定向，避免3xx跳转）
            response = requests.post(
                URL, 
                data=params, 
                headers=HEADERS, 
                timeout=20,  # 加长超时时间
                allow_redirects=False
            )
            response.raise_for_status()  # 抛出HTTP错误（4xx/5xx）
            response_data = response.json()
            
            # 6. 打印原始返回（排查500必备）
            if SHOW_DETAIL_LOG:
                print(f"📜 账号 {account_name} 第 {attempt+1} 次原始返回：{response_data}")
            
            # 7. 解析结果
            status_text = format_sign_status(response_data)
            print(f"\n📌 账号 {account_name} 第 {attempt+1} 次签到结果：\n{status_text}")
            
            # 8. 判断是否签到成功（根据返回码）
            code = response_data.get("status", {}).get("code")
            if code == 0:
                print(f"✅ 账号 {account_name} 签到成功！")
                return True, status_text, account_name
            else:
                error_msg = f"❌ 账号 {account_name} 第 {attempt+1} 次签到失败：{status_text}"
                # 若还有重试次数，打印重试提示
                if attempt < RETRY_TIMES:
                    print(f"⚠️ {error_msg}，{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    return False, error_msg, account_name
        
        except requests.exceptions.HTTPError as e:
            # 捕获500/4xx等HTTP错误
            error_msg = f"❌ 账号 {account_name} 第 {attempt+1} 次HTTP异常：{str(e)} | 响应码：{response.status_code if 'response' in locals() else '未知'}"
            if attempt < RETRY_TIMES:
                print(f"⚠️ {error_msg}，{RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
            else:
                print(error_msg)
                return False, error_msg, account_name
        except requests.exceptions.RequestException as e:
            # 捕获连接超时/网络错误等
            error_msg = f"❌ 账号 {account_name} 第 {attempt+1} 次请求异常：{str(e)}"
            if attempt < RETRY_TIMES:
                print(f"⚠️ {error_msg}，{RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
            else:
                print(error_msg)
                return False, error_msg, account_name
        except Exception as e:
            # 捕获其他未知异常
            error_msg = f"❌ 账号 {account_name} 第 {attempt+1} 次执行异常：{str(e)}"
            if attempt < RETRY_TIMES:
                print(f"⚠️ {error_msg}，{RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
            else:
                print(error_msg)
                return False, error_msg, account_name
    
    # 所有重试都失败
    final_error = f"❌ 账号 {account_name} 重试 {RETRY_TIMES} 次后仍失败"
    print(final_error)
    return False, final_error, account_name

def main():
    """主函数：执行签到逻辑"""
    print("="*60)
    print(f"🚀 milwaukeetool 自动签到启动 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 从环境变量读取核心凭证（GitHub Secrets 注入）
    client_id = os.getenv("MILWAUKEETOOL_CLIENT_ID", "")
    token_list = os.getenv("MILWAUKEETOOL_TOKEN_LIST", "")  # 你的 KEY 对应这个参数
    tokens = [t.strip() for t in token_list.split(",") if t.strip()]
    
    # 校验核心凭证
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
    
    # 执行多账号签到
    failed_list = []
    success_count = 0
    total_count = len(tokens)
    
    for idx, token in enumerate(tokens, 1):
        account_name = f"账号{idx}"
        # 账号间增加间隔，避免高频请求
        if idx > 1:
            account_delay = random.uniform(5, 10)
            print(f"\n⏳ 账号间间隔 {account_delay:.2f} 秒...")
            time.sleep(account_delay)
        # 处理单个账号
        success, msg, name = process_account(client_id, token, account_name)
        if success:
            success_count += 1
        else:
            failed_list.append((name, msg))
    
    # 汇总结果
    print("\n" + "="*60)
    print(f"📊 签到汇总 | 总数：{total_count} | 成功：{success_count} | 失败：{len(failed_list)}")
    print("="*60)
    
    # 失败推送
    if failed_list:
        push_title = f"❌ milwaukeetool签到失败 | {len(failed_list)}个账号异常"
        push_content = "### 失败账号详情：\n"
        for name, msg in failed_list:
            push_content += f"- **{name}**：\n{msg}\n\n"
        # 推送失败通知
        send_sendkey_notification(push_title, push_content)

if __name__ == "__main__":
    main()
