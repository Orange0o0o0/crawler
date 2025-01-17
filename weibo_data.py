import random
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import time
import csv
from driverUtils import driver
from weibo_data_functions import scrape_multiple_pages

# 打开微博首页
driver.get("https://s.weibo.com/")
time.sleep(random.randint(1, 2))  # 等待页面加载

# 加载保存的cookie
with open("cookies.json", "r") as file:
    cookies = json.load(file)

# 添加cookie到浏览器
for cookie in cookies:
    driver.add_cookie(cookie)

# 刷新页面，模拟已登录状态
driver.refresh()
time.sleep(random.randint(1, 2))  # 等待页面刷新和微博数据加载

# 获取微博输入框区域
search_input = driver.find_element(By.XPATH, '//div[@class="search-input"]/input[@type="text"]')
topic = input("请输入你想查询的微博话题\n")
search_input.send_keys(topic)
search_input.send_keys(u'\ue007')  # 模拟按下Enter键

# 输入待查询的页数
time_set = int(input("输入待查询的天数\n"))
data_list = scrape_multiple_pages(time_set, driver)

# 创建以关键词命名的文件夹
folder_name = f"{topic}_comments"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)

# 将数据保存为CSV文件
filename = f"{topic}_weibo_data.csv"  # 根据话题生成文件名

# 打开CSV文件进行写入
with open(filename, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # 写入CSV文件的标题行
    writer.writerow(["Topic", "id", "Author", "Time", "Content", "Like Count"])

    # 写入爬取的数据
    for data in data_list:
        writer.writerow([topic, data["id"], data["author"], data["time"], data["content"], data["like_count"]])

        # 将每条微博的评论数据保存为单独的文件，文件保存在以关键词命名的文件夹中
        comment_filename = os.path.join(folder_name, f"{data['id']}_comments.csv")  # 文件名使用微博ID
        with open(comment_filename, mode='w', newline='', encoding='utf-8') as comment_file:
            comment_writer = csv.writer(comment_file)
            # 写入评论数据的标题行
            comment_writer.writerow(["Comment Text", "Comment Time", "Comment User", "Comment Location", "Comment User ID"])

            # 写入每条评论
            for comment in data["comments"]:
                comment_writer.writerow([comment["comment_text"], comment["comment_time"], comment["comment_user"], comment["comment_location"], comment["comment_user_id"]])

print(f"数据已保存到 {filename}，每条微博的评论已保存在文件夹 {folder_name} 中。")

# 关闭浏览器
driver.quit()
