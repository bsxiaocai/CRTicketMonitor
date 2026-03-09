"""
车次收藏夹服务
负责管理用户收藏的车次列表
"""

import json
import os
from typing import List


class FavoriteService:
    """车次收藏服务"""

    def __init__(self, favorites_path: str):
        """
        初始化收藏服务
        :param favorites_path: favorites.json 文件路径
        """
        self.favorites_path = favorites_path
        self.favorites: List[str] = []
        self.load_favorites()

    def load_favorites(self) -> List[str]:
        """
        加载收藏列表
        :return: 收藏车次列表
        """
        if os.path.exists(self.favorites_path):
            try:
                with open(self.favorites_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.favorites = data.get("favorites", [])
            except Exception as e:
                print(f"警告：读取收藏文件失败：{e}")
                self.favorites = []
        else:
            self.favorites = []
        return self.favorites

    def save_favorites(self) -> bool:
        """
        保存收藏列表
        :return: 是否保存成功
        """
        try:
            with open(self.favorites_path, "w", encoding="utf-8") as f:
                json.dump({"favorites": self.favorites}, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"错误：保存收藏文件失败：{e}")
            return False

    def add_favorite(self, train_no: str) -> bool:
        """
        添加收藏车次
        :param train_no: 车次号
        :return: 是否添加成功
        """
        train_no_upper = train_no.upper().strip()
        if train_no_upper not in self.favorites:
            self.favorites.append(train_no_upper)
            return self.save_favorites()
        return False

    def remove_favorite(self, train_no: str) -> bool:
        """
        删除收藏车次
        :param train_no: 车次号
        :return: 是否删除成功
        """
        train_no_upper = train_no.upper().strip()
        if train_no_upper in self.favorites:
            self.favorites.remove(train_no_upper)
            return self.save_favorites()
        return False

    def get_favorites(self) -> List[str]:
        """
        获取收藏列表
        :return: 收藏车次列表
        """
        return self.favorites.copy()

    def is_favorite(self, train_no: str) -> bool:
        """
        判断车次是否已收藏
        :param train_no: 车次号
        :return: 是否已收藏
        """
        return train_no.upper().strip() in self.favorites

    def toggle_favorite(self, train_no: str) -> bool:
        """
        切换收藏状态
        :param train_no: 车次号
        :return: 切换后的状态（True=已收藏，False=已取消）
        """
        if self.is_favorite(train_no):
            self.remove_favorite(train_no)
            return False
        else:
            self.add_favorite(train_no)
            return True
