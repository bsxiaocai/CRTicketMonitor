"""
12306 API请求模块
负责与12306 API交互，获取车站编码和余票信息
"""

import os
import requests
import time
import re
import json
from typing import List, Optional


class TicketAPI:
    """12306票务API客户端"""

    def __init__(self, station_json_path: str, logger=None):
        """
        初始化API客户端
        :param station_json_path: 车站编码缓存文件路径
        :param logger: 可选的日志记录器
        """
        self.station_json = station_json_path
        self.logger = logger
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        }
        self.station_dict = {}
        self.code_to_name = {}

    def init_station_data(self) -> dict:
        """
        同步车站编码数据
        :return: 车站编码字典 {站名: 代码}
        """
        try:
            if self.logger:
                self.logger.debug("开始同步车站数据")

            url = f'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?v={time.time()}'
            res = self.session.get(url, timeout=10)
            matched = re.findall(r'([\u4e00-\u9fa5]+)\|([A-Z]+)', res.text)
            if matched:
                self.station_dict = {name: code for name, code in matched}
                with open(self.station_json, "w", encoding="utf-8") as f:
                    json.dump(self.station_dict, f, ensure_ascii=False, indent=4)
                if self.logger:
                    self.logger.debug(f"车站数据同步完成，共 {len(self.station_dict)} 个站点")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"车站数据同步失败，使用缓存: {e}")
            else:
                print(f"警告: 车站数据同步失败，使用缓存: {e}")

            if os.path.exists(self.station_json):
                try:
                    with open(self.station_json, "r", encoding="utf-8") as f:
                        self.station_dict = json.load(f)
                        if self.logger:
                            self.logger.debug(f"使用缓存车站数据，共 {len(self.station_dict)} 个站点")
                        else:
                            print(f"使用缓存车站数据，共 {len(self.station_dict)} 个站点")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"读取缓存车站数据失败: {e}", exc_info=True)
                    else:
                        print(f"错误: 读取缓存车站数据失败: {e}")

        self.code_to_name = {code: name for name, code in self.station_dict.items()}
        return self.station_dict

    def query_tickets(self, date: str, from_station: str, to_station: str) -> Optional[List[str]]:
        """
        查询余票信息
        :param date: 出发日期 (YYYY-MM-DD)
        :param from_station: 始发站名称
        :param to_station: 到达站名称
        :return: 车次列表，失败返回None，站名不匹配返回"STATION_NOT_FOUND"
        """
        # 检查站名是否存在
        from_code = self.station_dict.get(from_station)
        to_code = self.station_dict.get(to_station)

        if not from_code or not to_code:
            if self.logger:
                self.logger.error(f"站名匹配失败: {from_station}({from_code}) -> {to_station}({to_code})")
            return "STATION_NOT_FOUND"

        url = f"https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"
        try:
            self.session.get("https://kyfw.12306.cn/otn/leftTicket/init", headers=self.headers, timeout=5)
            response = self.session.get(url, headers=self.headers, timeout=10)
            result = response.json().get('data', {}).get('result', [])
            if self.logger:
                self.logger.debug(f"查询完成: {from_station} -> {to_station}, 返回 {len(result)} 条记录")
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"查询请求失败: {e}", exc_info=True)
            else:
                print(f"错误: 查询请求失败: {e}")
            return None

    def get_station_code(self, station_name: str) -> Optional[str]:
        """获取车站代码"""
        return self.station_dict.get(station_name)

    def get_station_name(self, station_code: str) -> Optional[str]:
        """获取车站名称"""
        return self.code_to_name.get(station_code)
