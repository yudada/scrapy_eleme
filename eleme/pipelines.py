# -*- coding: utf-8 -*-

import base64
import json
import sys
import traceback

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import mysql.connector

from eleme import settings
from eleme.mysqlhelper import *


class ElemePipeline(object):
    """处理所爬取的每个item，大部分为数据库操作
    """

    def process_item(self, item, spider):
        # 根据spider名称选择需要进行的操作
        if "geo_points" == spider.name:
            self.insert_point(item)
        elif "base_info" == spider.name:
            # 如果数据库中没有这个商家则插入，有这个商家则跳过
            if not self.select_restaurant_id(item["restaurant_id"]):
                self.insert_restaurant_info(item)
        elif "menu" == spider.name:
            self.insert_menu(item)
        elif "rating_scores" == spider.name:
            self.update_rating_scores(item)
        elif "location" == spider.name:
            self.update_location(item)

    def insert_point(self, item):
        """将坐标点放入数据库
        """
        sql = "INSERT INTO all_points (latitude, longitude) VALUES (%(latitude)s, %(longitude)s)"
        cur.execute(sql % item)
        cnx.commit()

    def update_location(self, item):
        """更新商家的位置信息(district, address)
        """
        sql = """
            UPDATE restaurant_info 
            SET district='%(district)s', address_baidu='%(address)s' 
            WhERE restaurant_id = %(restaurant_id)s
        """
        cur.execute(sql % item)
        cnx.commit()

    def insert_menu(self, item):
        """将菜单内容放入数据库
        """
        sql = "INSERT INTO menu_info (restaurant_id, menu) VALUES ('%s', '%s')"
        # 为避免一些很神奇的错误，先进行BASE64编码
        menu_data = base64.b64encode(item["menu"].encode("utf-8")).decode()
        cur.execute(sql % (item["restaurant_id"], menu_data))
        cnx.commit()

    def update_rating_scores(self, item):
        """更新商家的评分信息
        """
        keys = ["compare_rating", "food_score", "positive_rating", "service_score", "star_level"]
        if keys[0] in item.keys():
            item_keys = item.keys()
            key_value = ["`%s`='%s'" % (key, item[key]) for key in item_keys if key != "restaurant_id"]
        else:
            key_value = ["`%s`='-1'" % key for key in keys]
        key_value = ", ".join(key_value)
        sql = "UPDATE restaurant_info SET %s WhERE restaurant_id = %s"
        sql = sql % (key_value, item["restaurant_id"])
        cur.execute(sql)
        cnx.commit()

    def insert_restaurant_info(self, item):
        """将商家放入数据库
        """
        keys = item.keys()
        value_format = ["'%({})s'".format(key) for key in keys]
        sql = "INSERT INTO restaurant_info (%s) VALUES (%s);" % (
            ", ".join(keys),
            ", ".join(value_format)
        )
        value = {}
        for key in keys:
            # 如果是可迭代对象但不是字符串（比如dict或list）
            # 则先转换为JSON字符串，再进行BASE64编码，再插入数据库
            if hasattr(item[key], "__iter__") and not isinstance(item[key], str):
                value_str = json.dumps(item[key], ensure_ascii=False).encode("utf-8")
                value[key] = base64.b64encode(value_str).decode()
            else:
                value[key] = item[key]

        cur.execute(sql % value)
        cnx.commit()

    def select_restaurant_id(self, restaurant_id):
        """判断商家是否存在于数据库中
        """
        sql = "SELECT * FROM restaurant_info WHERE restaurant_id = %s"
        cur.execute(sql % restaurant_id)
        return cur.fetchall()
