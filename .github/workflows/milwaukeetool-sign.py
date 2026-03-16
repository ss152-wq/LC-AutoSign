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
GLOBAL_METHOD = "add.signon.item"  # 签到方法
# GLOBAL_METHOD = "get.signon.list"  # 查看签到天数

GLOBAL_STYPE = 1

# 【通知配置】Server酱 Turbo版 SendKey
# 替换为你的Server酱 SendKey（从https://sct.ftqq.com/获取）
SERVERCHAN_SENDKEY = "你的Server酱SendKey"

# 【调试开关】True: 打印完整返回JSON; False: 仅失败时打印
SHOW_RAW_RESPONSE = True

# 固定配置（无需修改）
SECRET = "36affdc58f50e1035649abc808c22b48"
APPKEY = "76472358"
PLATFORM = "MP-WEIXIN"
FORMAT = "json"
URL = "https://service.milwaukeetool.cn/api/v1/signon"

HEADERS = {
    "Host": "service.milwaukeetool.cn",
    "Connection": "keep-alive",
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

# ================= 工具函数 =================
def generate_sign(params):
    """生成签名"""
    try:
        # 排序参数
        sorted_params = sorted(params.items())
        # 拼接参数字符串
        param_str = ''.join([f"{k}{v}" for k, v in sorted_params])
        # 拼接secret并加密
        sign_str = param_str + SECRET
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        return sign
    except Exception as e:
        print(f"生成签名失败: {str(e)}")
        return ""

def send_serverchan_notification(failed_accounts, total_count, success_count):
    """发送Server酱通知"""
    # 校验SendKey有效性
    if not SERVERCHAN_SENDKEY or SERVERCHAN_SENDKEY == "你的Server酱SendKey":
        print("\n⚠️  未配置有效的Server酱 SendKey，跳过通知发送。")
        return

    # 构建通知标题和内容
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"米沃奇签到任务执行结果 | 成功{success_count}个 | 失败{len(failed_accounts)}个"
    
    # 构建失败详情
    if failed_accounts:
        fail_details = "\n".join([f"• {name}: {reason}" for name, reason in failed_accounts])
        content = (
            f"🤖 **米沃奇签到任务执行报告**\n"
            f"📅 执行时间: {now_str}\n"
            f"--------------------------\n"
            f"✅ 成功账号数: {success_count} 个\n"
            f"❌ 失败账号数: {len(failed_accounts)} 个\n"
            f"📂 总账号数: {total_count} 个\n"
            f"--------------------------\n"
            f"⚠️ **失败详情:**\n{fail_details}"
        )
    else:
        content = (
            f"🤖 **米沃奇签到任务执行报告**\n"
            f"📅 执行时间: {now_str}\n"
            f"--------------------------\n"
            f"🎉 所有账号签到成功！\n"
            f"✅ 成功账号数: {success_count} 个\n"
            f"📂 总账号数: {total_count} 个\n"
        )

    # 发送请求到Server酱API
    try:
        # Server酱 Turbo版 API地址
        api_url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
        payload = {
            "title": title,
            "desp": content
        }
        resp = requests.post(api_url, data=payload, timeout=10)
        resp_json = resp.json()
        
        if resp_json.get("code") == 0:
            print("\n📢 Server酱通知发送成功！")
        else:
            print(f"\n⚠️  Server酱通知发送失败: {resp_json.get('message', '未知错误')}")
    except Exception as e:
        print(f"\n⚠️  Server酱通知发送异常: {str(e)}")

def process_account(account_info, index, total, failed_list):
    """处理单个账号签到"""
    # 初始化账号名称
    name = account_info if isinstance(account_info, str) else f"账号{index + 1}"
    
    # 获取环境变量中的token和client_id
    token = os.getenv('MILWAUKEETOOL_TOKEN_LIST', '')
    client_id = os.getenv('MILWAUKEETOOL_CLIENT_ID', '')
    
    # 脱敏显示token
    token_show = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"

    print(f"\n[{index + 1}/{total}] 处理账号: {name}")
    print(f"      ├─ 方法: {GLOBAL_METHOD}")
    print(f"      ├─ ID: {client_id}")
    print(f"      └─ Token: {token_show}")

    # 校验必要参数
    if not token or not client_id:
        msg = "缺少 token 或 client_id 环境变量"
        print(f"      ❌ 结果: {msg}")
        failed_list.append((name, msg))
        return False

    try:
        # 构建请求参数
        timestamp = str(int(time.time()))
        nonce = str(random.randint(100000, 999999))
        
        params = {
            "appKey": APPKEY,
            "clientId": client_id,
            "format": FORMAT,
            "method": GLOBAL_METHOD,
            "nonce": nonce,
            "platform": PLATFORM,
            "stype": GLOBAL_STYPE,
            "timestamp": timestamp,
            "token": token
        }
        
        # 生成签名
        sign = generate_sign(params)
        if not sign:
            msg = "签名生成失败"
            print(f"      ❌ 结果: {msg}")
            failed_list.append((name, msg))
            return False
        
        params["sign"] = sign
        
        # 发送请求
        response = requests.post(
            URL,
            headers=HEADERS,
            json=params,
            timeout=15
        )
        
        response.raise_for_status()
        result = response.json()
        
        # 调试模式打印完整返回
        if SHOW_RAW_RESPONSE:
            print(f"      ├─ 原始响应: {json.dumps(result, ensure_ascii=False)}")
        
        # 处理响应结果
        if result.get("code") == 200:
            if GLOBAL_METHOD == "add.signon.item":
                print(f"      ✅ 结果: 签到成功")
            else:
                sign_days = result.get("data", {}).get("signonDays", 0)
                print(f"      ✅ 结果: 查询成功，累计签到{sign_days}天")
            return True
        else:
            msg = f"接口返回错误: {result.get('msg', '未知错误')} (code: {result.get('code')})"
            print(f"      ❌ 结果: {msg}")
            failed_list.append((name, msg))
            return False
            
    except requests.exceptions.Timeout:
        msg = "请求超时"
        print(f"      ❌ 结果: {msg}")
        failed_list.append((name, msg))
        return False
    except requests.exceptions.RequestException as e:
        msg = f"网络请求失败: {str(e)}"
        print(f"      ❌ 结果: {msg}")
        failed_list.append((name, msg))
        return False
    except Exception as e:
        msg = f"处理失败: {str(e)}"
        print(f"      ❌ 结果: {msg}")
        failed_list.append((name, msg))
        return False

# ================= 主函数 =================
def main():
    print("=" * 60)
    print(f"🚀 米沃奇批量签到启动 | 模式: {GLOBAL_METHOD}")
    print(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    success_count = 0
    failed_list = []  # 存储 (名字, 原因)
    
    # 读取账号列表（支持多账号，这里默认单账号）
    # 如需多账号，可修改为从环境变量读取账号列表
    accounts = ["米沃奇账号1"]
    total_accounts = len(accounts)

    # 遍历处理每个账号
    for idx, account_name in enumerate(accounts):
        if process_account(account_name, idx, total_accounts, failed_list):
            success_count += 1
        # 避免请求过快，添加随机延迟
        time.sleep(random.uniform(1, 3))

    # 输出汇总结果
    print("\n" + "=" * 60)
    print(f"🏁 签到任务执行完成")
    print(f"   📊 总计账号: {total_accounts}")
    print(f"   ✅ 成功签到: {success_count}")
    print(f"   ❌ 签到失败: {len(failed_list)}")
    print("=" * 60)

    # 发送Server酱通知
    send_serverchan_notification(failed_list, total_accounts, success_count)

    # 返回执行状态（用于CI/CD）
    if len(failed_list) > 0:
        exit(1)
    else:
        exit(0)

# ================= 执行入口 =================
if __name__ == "__main__":
    main()
