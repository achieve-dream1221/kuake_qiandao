import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pprint import pprint
from loguru import logger
import httpx
import os

# 夸克
kps = os.getenv("QUARK_KPS")
sign = os.getenv("QUARK_SIGN")
vcode = os.getenv("QUARK_VCODE")

if kps is None or sign is None or vcode is None:
    logger.error("请设置 QUARK_KPS 或者 QUARK_SIGN 或者 QUARK_VCODE")
    raise ValueError("请设置 QUARK_KPS 或者 QUARK_SIGN 或者 QUARK_VCODE")

# 邮箱通知
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT", default=587)  # 587 TLS 端口，使用 465 代表 SSL
EMAIL = os.getenv("EMAIL")  # 你的邮箱
PASSWORD = os.getenv("PASSWORD")  # 你的 SMTP 授权码（不是邮箱密码）

config_is_ok = False

if SMTP_SERVER is not None and SMTP_PORT is not None and EMAIL is not None and PASSWORD is not None:
    config_is_ok = True


def query_balance():
    """
    查询抽奖余额
    """
    url = "https://coral2.quark.cn/currency/v1/queryBalance"
    querystring = {
        "moduleCode": "1f3563d38896438db994f118d4ff53cb",
        "kps": kps,
    }
    response = httpx.get(url=url, params=querystring)
    response.raise_for_status()
    pprint(response.json())


def human_unit(bytes_: int) -> str:
    """
    人类可读单位
    :param bytes_: 字节数
    :return: 返回 MB GB TB
    """
    units = ("MB", "GB", "TB", "PB")
    bytes_ = bytes_ / 1024 / 1024
    i = 0
    while bytes_ >= 1024:
        bytes_ /= 1024
        i += 1
    return f"{bytes_:.2f} {units[i]}"


def send_email(body: str):
    SUBJECT = "夸克网盘自动签到"
    try:
        # 创建邮件对象
        msg = MIMEMultipart()
        msg["From"] = EMAIL
        msg["To"] = EMAIL
        msg["Subject"] = SUBJECT
        # 添加邮件正文
        msg.attach(MIMEText(body, "plain"))

        # 连接 SMTP 服务器
        if int(SMTP_PORT) == 587:
            server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
            server.starttls()  # 启用 TLS 加密
        elif int(SMTP_PORT) == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, int(SMTP_PORT))
        server.login(EMAIL, PASSWORD)  # 登录 SMTP 服务器
        server.sendmail(EMAIL, EMAIL, msg.as_string())  # 发送邮件
        server.quit()  # 关闭连接
    except Exception as e:
        print(f"邮件发送失败: {e}")


def user_info():
    """
    获取用户信息
    :return: None
    """
    url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
    querystring = {
        "pr": "ucpro",
        "fr": "android",
        "kps": kps,
        "sign": sign,
        "vcode": vcode,
    }
    response = httpx.get(url=url, params=querystring)
    response.raise_for_status()
    content = response.json()
    if content["code"] != 0:
        logger.warning(content["message"])
    else:
        data = content["data"]
        super_vip_exp_at = datetime.fromtimestamp(
            data["super_vip_exp_at"] / 1000
        ).strftime("%Y-%m-%d %H:%M:%S")
        cap_sign = data["cap_sign"]
        notify_message = ""
        if cap_sign["sign_daily"]:
            notify_message += (f"今日已签到，获得容量: {human_unit(cap_sign['sign_daily_reward'])},"
                               f" 签到进度: {cap_sign['sign_progress']}\n")
        notify_message += (f"会员类型：{data['member_type']}, 过期时间：{super_vip_exp_at}, 总计容量："
                           f"{human_unit(data['total_capacity'])}, 使用容量：{human_unit(data['use_capacity'])}, "
                           f"使用百分比：{data['use_capacity'] / data['total_capacity'] * 100:.2f}%")
        logger.info(notify_message)
        if config_is_ok:
            send_email(notify_message)


def checkin():
    """
    签到
    :return: None
    """
    url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
    querystring = {
        "pr": "ucpro",
        "fr": "android",
        "kps": kps,
        "sign": sign,
        "vcode": vcode,
    }
    response = httpx.post(url=url, json={"sign_cyclic": True}, params=querystring)
    if response.status_code == 200:
        if response.json()["code"] != 0:
            logger.warning(response.json()["message"])
        else:
            logger.success(
                f"签到成功，获得容量: {human_unit(response.json()['data']['sign_daily_reward'])}"
            )
    else:
        logger.warning(f"已经签到，请勿重复签到")


if __name__ == "__main__":
    checkin()
    user_info()
