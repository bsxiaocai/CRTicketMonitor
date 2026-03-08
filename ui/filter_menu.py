"""
筛选菜单模块
负责车次筛选和排序
"""

import os
import time


class FilterMenu:
    """筛选菜单"""

    @staticmethod
    def show_filter_menu(current_filters: dict, all_tickets=None) -> tuple:
        """
        二级筛选菜单
        :param current_filters: 当前筛选状态
        :param all_tickets: 车票列表（用于显示可选车站）
        :return: (should_continue, updated_filters)
        """
        # 从车票数据中提取可选车站列表
        from_stations = []
        to_stations = []
        if all_tickets:
            from_stations = sorted(set(t.from_station for t in all_tickets))
            to_stations = sorted(set(t.to_station for t in all_tickets))

        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*80)
            print("=== 筛选与排序菜单 ===")
            print("="*80)

            type_str = current_filters['type'] or '全部'
            from_str = current_filters['from'] or '全部'
            to_str = current_filters['to'] or '全部'
            period_map = {None: '全部时段', 0: '00:00-06:00', 1: '06:00-12:00', 2: '12:00-18:00', 3: '18:00-24:00'}
            period_str = period_map.get(current_filters['time_period'], '全部时段')
            sort_map = {
                None: '无', 'earliest_depart': '最早发车', 'latest_depart': '最晚发车',
                'earliest_arrival': '最早到达', 'latest_arrival': '最晚到达',
                'shortest': '最短历时', 'longest': '最长历时'
            }
            sort_str = sort_map.get(current_filters['sort'], '无')

            print(f"\n【当前筛选】")
            print(f"  车型: {type_str} | 始发: {from_str} | 到达: {to_str}")
            print(f"  时段: {period_str} | 排序: {sort_str}")
            print("-" * 80)

            print("[车型筛选]  1.全部  2.高铁动车  3.普通车")
            print("[站点筛选]  4.始发站  5.到达站")
            print("[时段筛选]  6.全部时段  7.00:00-06:00  8.06:00-12:00  9.12:00-18:00  0.18:00-24:00")
            print("[排序选项]  A.最早发车  B.最晚发车  C.最早到达  D.最晚到达  E.最短历时  F.最长历时")
            print("[其他]      R.重置筛选  X.返回主查询")
            print("-" * 80)

            try:
                choice = input("请输入选项 (1-9, 0, A-F, R, X): ").strip().lower()

                # 车型筛选 (1-3)
                if choice == '1':
                    current_filters['type'] = None
                    print("\n[✓] 车型筛选已重置为：全部")
                    time.sleep(0.5)
                elif choice == '2':
                    current_filters['type'] = "高铁动车"
                    print("\n[✓] 车型筛选已设置为：高铁动车")
                    time.sleep(0.5)
                elif choice == '3':
                    current_filters['type'] = "普通车"
                    print("\n[✓] 车型筛选已设置为：普通车")
                    time.sleep(0.5)

                # 站点筛选 (4-5)
                elif choice == '4':
                    if from_stations:
                        print("\n【可选始发站】")
                        for i, station in enumerate(from_stations, 1):
                            print(f"  {i}. {station}")
                        print("  0. 全部")
                        try:
                            sel = input("\n请选择 (输入序号): ").strip()
                            if sel == '0' or sel == '':
                                current_filters['from'] = None
                                print("\n[✓] 始发站筛选已重置为：全部")
                            else:
                                idx = int(sel) - 1
                                if 0 <= idx < len(from_stations):
                                    current_filters['from'] = from_stations[idx]
                                    print(f"\n[✓] 始发站筛选已设置为：{from_stations[idx]}")
                                else:
                                    print("\n[!] 无效选择")
                        except ValueError:
                            print("\n[!] 请输入有效数字")
                    else:
                        print("\n[提示] 暂无车站数据，请先执行查询")
                        new_from = input("输入始发站名称（按回车键跳过）: ").strip()
                        current_filters['from'] = new_from if new_from else None
                        print(f"\n[✓] 始发站筛选已设置为：{new_from if new_from else '全部'}")
                    time.sleep(0.5)
                elif choice == '5':
                    if to_stations:
                        print("\n【可选到达站】")
                        for i, station in enumerate(to_stations, 1):
                            print(f"  {i}. {station}")
                        print("  0. 全部")
                        try:
                            sel = input("\n请选择 (输入序号): ").strip()
                            if sel == '0' or sel == '':
                                current_filters['to'] = None
                                print("\n[✓] 到达站筛选已重置为：全部")
                            else:
                                idx = int(sel) - 1
                                if 0 <= idx < len(to_stations):
                                    current_filters['to'] = to_stations[idx]
                                    print(f"\n[✓] 到达站筛选已设置为：{to_stations[idx]}")
                                else:
                                    print("\n[!] 无效选择")
                        except ValueError:
                            print("\n[!] 请输入有效数字")
                    else:
                        print("\n[提示] 暂无车站数据，请先执行查询")
                        new_to = input("输入到达站名称（按回车键跳过）: ").strip()
                        current_filters['to'] = new_to if new_to else None
                        print(f"\n[✓] 到达站筛选已设置为：{new_to if new_to else '全部'}")
                    time.sleep(0.5)

                # 时段筛选 (6-0)
                elif choice == '6':
                    current_filters['time_period'] = None
                    print("\n[✓] 时段筛选已重置为：全部时段")
                    time.sleep(0.5)
                elif choice == '7':
                    current_filters['time_period'] = 0
                    print("\n[✓] 时段筛选已设置为：00:00-06:00")
                    time.sleep(0.5)
                elif choice == '8':
                    current_filters['time_period'] = 1
                    print("\n[✓] 时段筛选已设置为：06:00-12:00")
                    time.sleep(0.5)
                elif choice == '9':
                    current_filters['time_period'] = 2
                    print("\n[✓] 时段筛选已设置为：12:00-18:00")
                    time.sleep(0.5)
                elif choice == '0':
                    current_filters['time_period'] = 3
                    print("\n[✓] 时段筛选已设置为：18:00-24:00")
                    time.sleep(0.5)

                # 排序选项 (A-F)
                elif choice == 'a':
                    current_filters['sort'] = 'earliest_depart'
                    print("\n[✓] 排序方式已设置为：最早发车")
                    time.sleep(0.5)
                elif choice == 'b':
                    current_filters['sort'] = 'latest_depart'
                    print("\n[✓] 排序方式已设置为：最晚发车")
                    time.sleep(0.5)
                elif choice == 'c':
                    current_filters['sort'] = 'earliest_arrival'
                    print("\n[✓] 排序方式已设置为：最早到达")
                    time.sleep(0.5)
                elif choice == 'd':
                    current_filters['sort'] = 'latest_arrival'
                    print("\n[✓] 排序方式已设置为：最晚到达")
                    time.sleep(0.5)
                elif choice == 'e':
                    current_filters['sort'] = 'shortest'
                    print("\n[✓] 排序方式已设置为：最短历时")
                    time.sleep(0.5)
                elif choice == 'f':
                    current_filters['sort'] = 'longest'
                    print("\n[✓] 排序方式已设置为：最长历时")
                    time.sleep(0.5)

                # 重置筛选
                elif choice == 'r':
                    current_filters['type'] = None
                    current_filters['from'] = None
                    current_filters['to'] = None
                    current_filters['time_period'] = None
                    current_filters['sort'] = None
                    print("\n[✓] 所有筛选条件已重置")
                    time.sleep(0.5)

                # 返回主查询
                elif choice == 'x':
                    return (True, current_filters)

                else:
                    print("\n[!] 无效选择")
                    time.sleep(0.5)

            except KeyboardInterrupt:
                return (True, current_filters)
