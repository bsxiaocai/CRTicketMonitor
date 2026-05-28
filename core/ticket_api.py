"""
12306 API请求模块
负责与12306 API交互，获取车站编码和余票信息
"""

import os
import requests
import time
import re
import json
from typing import Dict, List, Optional
from datetime import datetime


class TicketAPI:
    """12306票务API客户端"""

    def __init__(self, station_json_path: str, logger=None, debug_api: bool = False):
        """
        初始化API客户端
        :param station_json_path: 车站编码缓存文件路径
        :param logger: 可选的日志记录器
        :param debug_api: 是否启用API调试日志
        """
        self.station_json = station_json_path
        self.logger = logger
        self.debug_api = debug_api
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        }
        self.station_dict = {}
        self.code_to_name = {}
        self._price_cache = {}
        self._api_log_file = None
        self._init_session_done = False

    def _request_with_retry(self, url: str, params: dict = None, timeout: int = 10, max_retries: int = 3) -> Optional[requests.Response]:
        """
        带重试机制的HTTP请求
        :param url: 请求URL
        :param params: 查询参数
        :param timeout: 超时时间（秒）
        :param max_retries: 最大重试次数
        :return: Response对象，失败返回None
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, headers=self.headers, timeout=timeout)
                self._debug_response(url, response)
                return response
            except requests.RequestException as e:
                last_exception = e
                if self.logger:
                    self.logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {url}, 错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (2 ** attempt))  # 指数退避：1s, 2s, 4s
        if self.logger:
            self.logger.error(f"请求最终失败: {url}, 最后错误: {last_exception}")
        return None

    def _init_api_log_file(self) -> None:
        """初始化API日志文件"""
        if self._api_log_file:
            return

        try:
            log_dir = os.path.join(os.path.dirname(self.station_json), "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "api_responses.log")
            self._api_log_file = open(log_path, "a", encoding="utf-8")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"无法创建API日志文件: {e}")
            self._api_log_file = None

    def _debug_response(self, url: str, response: requests.Response) -> None:
        """
        调试响应信息
        :param url: 请求URL
        :param response: Response对象
        """
        if self.logger:
            self.logger.debug(f"请求URL: {url}")
            self.logger.debug(f"响应状态码: {response.status_code}")
            try:
                response_text = response.text[:500] if response.text else ""
                self.logger.debug(f"响应内容: {response_text}")
            except Exception:
                pass

        # 写入API日志文件（如果启用调试模式）
        if self.debug_api:
            self._init_api_log_file()
            if self._api_log_file:
                try:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    log_entry = f"[{timestamp}] URL: {url}\n"
                    log_entry += f"[{timestamp}] 状态码: {response.status_code}\n"
                    response_text = response.text[:1000] if response.text else ""
                    log_entry += f"[{timestamp}] 响应内容: {response_text}\n"
                    log_entry += "-" * 80 + "\n"
                    self._api_log_file.write(log_entry)
                    self._api_log_file.flush()
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"写入API日志失败: {e}")

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
            # 首次查询访问init页面建立session，后续跳过
            if not self._init_session_done:
                resp = self._request_with_retry("https://kyfw.12306.cn/otn/leftTicket/init", timeout=5)
                if resp is not None:
                    self._init_session_done = True

            # 使用带重试的请求查询余票
            response = self._request_with_retry(url, timeout=10)
            if not response:
                if self.logger:
                    self.logger.error(f"查询请求失败: 无响应")
                return None

            # 检查HTTP状态码
            if response.status_code != 200:
                if self.logger:
                    self.logger.error(f"查询请求失败: HTTP {response.status_code}")
                return None

            # 解析JSON响应
            try:
                json_data = response.json()
            except ValueError as e:
                if self.logger:
                    self.logger.error(f"查询响应不是有效JSON: {e}")
                    self.logger.debug(f"响应内容: {response.text[:200]}")
                return None

            # 验证响应结构
            data = json_data.get('data')
            if not data or not isinstance(data, dict):
                if self.logger:
                    self.logger.warning(f"查询响应结构异常: {json_data}")
                return None

            result = data.get('result', [])
            if not isinstance(result, list):
                if self.logger:
                    self.logger.warning(f"查询结果不是列表: {result}")
                return []

            if self.logger:
                self.logger.info(f"查询完成: {from_station} -> {to_station}, 返回 {len(result)} 条记录")
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

    def clear_price_cache(self) -> None:
        """清除票价缓存"""
        self._price_cache.clear()
        if self.logger:
            self.logger.info("票价缓存已清除")

    def __del__(self):
        """析构时确保关闭文件句柄"""
        self.close()

    def close(self) -> None:
        """关闭API客户端，释放资源"""
        if self._api_log_file:
            try:
                self._api_log_file.close()
            except Exception:
                pass
            self._api_log_file = None

    # 票价 API key → 显示名映射
    PRICE_SEAT_MAP = {
        "A9": "商/特", "9": "商/特", "P": "商/特",
        "M": "一等座",
        "O": "二等座",
        "A4": "一等/软卧", "4": "一等/软卧",
        "A3": "二等/硬卧", "3": "二等/硬卧",
        "1": "硬座",
        "WZ": "无座",
        "A6": "高级软卧", "6": "高级软卧",
    }

    def query_ticket_price(self, train_no: str, from_station_no: str,
                           to_station_no: str, seat_types: str,
                           train_date: str) -> Optional[Dict[str, str]]:
        """
        查询票价
        :param train_no: 内部车次号（d[2]）
        :param from_station_no: 出发站序号（d[16]）
        :param to_station_no: 到达站序号（d[17]）
        :param seat_types: 席别代码串（d[35]）
        :param train_date: 出发日期（YYYY-MM-DD）
        :return: {席别显示名: 价格} 字典，失败返回 None
        """
        # 检查缓存
        cache_key = f"{train_no}_{from_station_no}_{to_station_no}_{train_date}"
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]

        url = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice"
        params = {
            "train_no": train_no,
            "from_station_no": from_station_no,
            "to_station_no": to_station_no,
            "seat_types": seat_types,
            "train_date": train_date,
            "purpose_codes": "ADULT",
        }

        try:
            # 使用带重试的请求
            response = self._request_with_retry(url, params=params, timeout=10)
            if not response:
                if self.logger:
                    self.logger.warning(f"票价查询失败: {train_no}: 无响应")
                return None

            # 检查HTTP状态码
            if response.status_code != 200:
                if self.logger:
                    self.logger.warning(f"票价查询失败: {train_no}: HTTP {response.status_code}")
                return None

            # 解析JSON响应
            try:
                json_data = response.json()
            except ValueError as e:
                if self.logger:
                    self.logger.warning(f"票价查询响应不是有效JSON: {train_no}: {e}")
                return None

            # 验证响应结构
            price_data = json_data.get("data")
            if not price_data or not isinstance(price_data, dict):
                if self.logger:
                    self.logger.debug(f"票价查询无数据: {train_no}")
                return None

            # 将 API key 映射到显示名
            result = {}
            for api_key, display_name in self.PRICE_SEAT_MAP.items():
                if api_key in price_data and price_data[api_key]:
                    result[display_name] = str(price_data[api_key])

            # 如果没有匹配到任何票价，记录实际返回的键
            if not result and price_data:
                if self.logger:
                    self.logger.warning(f"票价查询未匹配到席别: {train_no}, API返回的键: {list(price_data.keys())}")

            self._price_cache[cache_key] = result
            if self.logger:
                self.logger.info(f"票价查询成功: {train_no}, {len(result)} 个席别, 票价: {result}")
            return result
        except Exception as e:
            if self.logger:
                self.logger.warning(f"票价查询失败: {train_no}: {e}")
            return None

    def query_transfer(self, date: str, from_station: str, to_station: str) -> Optional[dict]:
        """
        查询中转换乘方案
        :param date: 出发日期（YYYY-MM-DD）
        :param from_station: 始发站名称
        :param to_station: 到达站名称
        :return: API 返回的 data 字典，包含 result 列表和 map 映射；失败返回 None 或 "STATION_NOT_FOUND"
        """
        from_code = self.station_dict.get(from_station)
        to_code = self.station_dict.get(to_station)

        if not from_code or not to_code:
            if self.logger:
                self.logger.error(f"中转查询站名匹配失败: {from_station}({from_code}) -> {to_station}({to_code})")
            return "STATION_NOT_FOUND"

        url = (
            f"https://kyfw.12306.cn/otn/leftTicket/queryZ"
            f"?leftTicketDTO.train_date={date}"
            f"&leftTicketDTO.from_station={from_code}"
            f"&leftTicketDTO.to_station={to_code}"
            f"&purpose_codes=ADULT"
        )
        try:
            # 首次查询访问init页面建立session，后续跳过
            if not self._init_session_done:
                resp = self._request_with_retry("https://kyfw.12306.cn/otn/leftTicket/init", timeout=5)
                if resp is not None:
                    self._init_session_done = True

            # 使用带重试的请求查询中转
            response = self._request_with_retry(url, timeout=15)
            if not response:
                if self.logger:
                    self.logger.error(f"中转查询请求失败: 无响应")
                return None

            # 检查HTTP状态码
            if response.status_code != 200:
                if self.logger:
                    self.logger.error(f"中转查询请求失败: HTTP {response.status_code}")
                return None

            # 解析JSON响应
            try:
                json_data = response.json()
            except ValueError as e:
                if self.logger:
                    self.logger.error(f"中转查询响应不是有效JSON: {e}")
                return None

            # 验证响应结构
            result = json_data.get('data', {})
            if not result or not isinstance(result, dict):
                if self.logger:
                    self.logger.warning(f"中转查询响应结构异常: {json_data}")
                return {}

            if self.logger:
                count = len(result.get('result', [])) if isinstance(result, dict) else 0
                self.logger.info(f"中转查询完成: {from_station} -> {to_station}, 返回 {count} 条记录")
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"中转查询请求失败: {e}", exc_info=True)
            return None
