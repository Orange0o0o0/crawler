import random
from selenium.webdriver.common.by import By
import time
from datetime import datetime, timedelta
import re
import requests

# 获取过去n天的日期
def get_date_n_days_ago(n):
    today = datetime.now()
    past_date = today - timedelta(days=n)
    return past_date

# 判断微博的发布时间是否在过去n天内
def is_post_within_days(post_time, days):
    """
    判断微博发布时间是否在指定的天数范围内。

    Args:
        post_time (str): 微博的发布时间字符串。
        days (int): 时间范围，单位为天。

    Returns:
        bool: 如果微博发布时间在范围内，则返回 True；否则返回 False。
    """
    # 当前时间
    now = datetime.now()
    try:
        # 尝试解析微博时间
        if "年" in post_time:  # 格式：2024年01月16日12:34
            post_datetime = datetime.strptime(post_time, "%Y年%m月%d日%H:%M")
        elif "月" in post_time and "日" in post_time:  # 格式：01月16日12:34 (无年份)
            post_datetime = datetime.strptime(post_time, "%m月%d日%H:%M")
            post_datetime = post_datetime.replace(year=now.year)  # 补充年份
        elif "小时前" in post_time:  # 格式：3小时前
            hours_ago = int(post_time.replace("小时前", "").strip())
            post_datetime = now - timedelta(hours=hours_ago)
        elif "分钟前" in post_time:  # 格式：30分钟前
            minutes_ago = int(post_time.replace("分钟前", "").strip())
            post_datetime = now - timedelta(minutes=minutes_ago)
        else:
            # 未知格式，记录并返回 False
            print(f"未知时间格式: {post_time}")
            return False

        # 判断是否在指定天数范围内
        return now - post_datetime <= timedelta(days=days)

    except Exception as e:
        print(f"时间解析错误: {post_time}, 错误信息: {str(e)}")
        return False


# 时间处理函数
def process_time(time_str):
    # 获取当前时间
    now = datetime.now()

    try:
        # 处理“分钟前”
        if "分钟前" in time_str:
            minutes = int(re.search(r"\d+", time_str).group(0))  # 提取数字部分
            processed_time = now - timedelta(minutes=minutes)

        # 处理“秒前”
        elif "秒前" in time_str:
            seconds = int(re.search(r"\d+", time_str).group(0))  # 提取数字部分
            processed_time = now - timedelta(seconds=seconds)

        # 处理“今天08:40”
        elif "今天" in time_str:
            time_part = re.search(r"\d{2}:\d{2}", time_str).group(0)
            # 转换为datetime对象
            time_obj = datetime.strptime(time_part, "%H:%M")
            # 使用当前日期和提取的时间生成新的时间
            processed_time = now.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)

        # 处理形如“10月07日23:12”的时间
        elif re.match(r"\d+月\d+日\d{2}:\d{2}", time_str):
            processed_time = datetime.strptime(time_str, "%m月%d日%H:%M")
            processed_time = processed_time.replace(year=now.year)

        # 处理形如“2023年10月02日10:02”的时间
        elif re.match(r"\d+年\d+月\d+日\d{2}:\d{2}", time_str):
            processed_time = datetime.strptime(time_str, "%Y年%m月%d日%H:%M")

        # 如果没有匹配到预期的时间格式，则抛出异常
        else:
            raise ValueError("无法解析的时间格式")

        # 字符串格式化，最终转换为指定格式
        return processed_time.strftime("%Y年%m月%d日%H:%M")

    except Exception as e:
        return f"解析错误: {e}"


# 列表推导式去除空格换行符制表符
def string_strip(str):
    return ''.join([i for i in str if i not in [' ', '\n']])


# 微博内容处理
def strip_message(str):
    return ''.join(char for char in str if
                   char.isalnum() or char in ['#', '@', ' ', '！', '。', '，', '？'] or ('a' <= char <= 'z') or (
                           'A' <= char <= 'Z'))


# 获取单页微博数据和评论
def get_page_data(driver):
    weibo_data = []
    # 获取所有微博卡片
    weibo_posts = driver.find_elements(By.XPATH, '//*[@id="pl_feedlist_index"]/div/div[@action-type="feed_list_item"]')
    for post in weibo_posts:
        try:
            try:
                expand_button = post.find_element(By.XPATH, './/a[@action-type="fl_unfold"]')
                expand_button.click()  # 点击展开全文
                time.sleep(random.randint(1, 2))  # 等待内容展开
                # 需要展开和不需要展开的XPATH路径不一样
                content = post.find_element(By.XPATH, './/p[@class="txt"and @node-type="feed_list_content_full"]').text
                content = content.replace("收起d", "")
            except:
                # 获取微博内容
                content = post.find_element(By.XPATH, './/p[@class="txt"]').text
                pass  # 如果没有展开按钮，继续正常流程
            content = string_strip(content)
            content = strip_message(content)
            # 获取发布者昵称
            author = post.find_element(By.XPATH, './/a[@class="name"]').text
            #  获取发布时间
            time_posted = post.find_element(By.XPATH, './/div[@class="from"]/a[@target="_blank"]').text
            time_posted = string_strip(time_posted)
            time_posted = process_time(time_posted)
            # 获取点赞数量
            like_count = post.find_element(By.XPATH, './/span[@class="woo-like-count"]').text
            if "赞" in like_count:
                like_count = like_count.replace("赞", "0")
            like_count = int(like_count)

            # 获取微博ID，构造评论URL
            weibo_id = post.get_attribute("mid")  # 获取微博的ID
            comment_url = f"https://weibo.com/ajax/statuses/buildComments?is_reload=1&id={weibo_id}&is_show_bulletin=3&is_mix=0&count=10&uid=1893892941&fetch_level=0&locale=zh-CN"
            print(f"微博ID: {weibo_id}, 评论URL: {comment_url}")

            # 获取评论数据
            comments = get_comments(comment_url)

            weibo_data.append({
                "id": weibo_id,
                "author": author,
                "content": content,
                "time": time_posted,
                "like_count": like_count,
                "comments": comments  # 存储评论
            })
        except Exception as e:
            print(f"遇到错误：{e}")
            continue
    return weibo_data


# 获取评论数据
def get_comments(comment_url):
    # 请求头
    headers = {
        # 用户身份信息
        'cookie': 'PC_TOKEN=d1691ba79a; SCF=ApH_4W76sDQf-kdiU4QJVbrsxRa_F9u8HkQtouOr4MMGZ4uLUPTeThK0PnqSFq3KFwg_HBvNCgfU6HVemyvw_No.; SUB=_2A25KjA6PDeRhGeBK7FAT8yrFyDSIHXVp4A5HrDV8PUNbmtAYLXfSkW1NR4cyeIjknIMa69EWIQoatFxsbRu_7xT7; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WhU5.PCTBa7LzvbnjCfULo_5NHD95QcShMEeoeX1KeRWs4Dqc_xi--Xi-zRiKy2i--fiKysi-8si--RiKn0i-i2i--Xi-zRiKy2i--fiK.ciKLhi--ci-8hi-2Ei--RiKn0i-2pi--RiK.7iKL2i--fiKy2iKLh; ALF=02_1739590623; XSRF-TOKEN=z_S1MQtLrbkVlIxhQrwEpOI4; _s_tentry=weibo.com; Apache=3943401715614.13.1736998720537; SINAGLOBAL=3943401715614.13.1736998720537; ULV=1736998720565:1:1:1:3943401715614.13.1736998720537:; WBPSESS=-NdLL32AIXLheH8D-CarN1AaPlLr68Nz0gwOOfWoXVhL4WrkTlIt0e8ArLGi4Kz4Fb9mU6M24dgEJz1cbWp5YzNzEU7AFE5nFUSZq__O5euUhV99rzVKFiZYiZxH4IXchC8efE8YeCcWKRgWtmqW5g==',
        # 防盗链
        'referer': 'https://weibo.com/1893892941/P9DyboeFl?refer_flag=1001030103_',
        # 浏览器基本信息
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
    }

    comments = []
    try:
        response = requests.get(comment_url, headers=headers)
        json_data = response.json()

        for comment in json_data['data']:
            comment_data = {
                "comment_text": comment['text_raw'],
                "comment_time": comment['created_at'],
                "comment_user": comment['user']['screen_name'],
                "comment_location": comment['user']['location'],
                "comment_user_id": comment['user']['id']
            }
            comments.append(comment_data)

    except Exception as e:
        print(f"获取评论时出错：{e}")

    return comments


# 抓取多页微博内容的函数
def scrape_multiple_pages(days, driver):
    """
    爬取多页微博数据，直到没有更多页面或超出指定时间范围为止。

    Args:
        days (int): 指定的时间范围，单位为天。
        driver (webdriver): Selenium WebDriver 实例。

    Returns:
        list: 包含所有符合条件的微博数据。
    """
    all_weibo_data = []
    while True:
        # 获取当前页面数据
        page_data = get_page_data(driver)
        if not page_data:
            break  # 当前页面没有数据，结束爬取

        # 检查数据时间范围
        valid_data = [data for data in page_data if is_post_within_days(data["time"], days)]
        all_weibo_data.extend(valid_data)

        # 如果当前页的所有数据都不在时间范围内，停止爬取
        if not valid_data:
            break

        # 尝试找到并点击“下一页”按钮
        try:
            next_button = driver.find_element(By.XPATH, "//a[contains(text(), '下一页')]")
            next_button.click()
            time.sleep(random.uniform(2, 5))  # 等待页面加载
        except Exception as e:
            print("没有找到更多页面:", str(e))
            break

    return all_weibo_data

