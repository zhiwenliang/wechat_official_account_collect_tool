"""
坐标校准工具
用于记录微信窗口中关键按钮的坐标位置
"""
import pyautogui
import json
import time
from pathlib import Path

def get_mouse_position():
    """获取当前鼠标位置"""
    return pyautogui.position()

def calibrate():
    """交互式坐标校准"""
    print("=== 微信公众号文章采集 - 坐标校准工具 ===\n")
    print("请按照提示将鼠标移动到指定位置，然后按回车键记录坐标")
    print("注意：校准后请勿移动窗口位置和大小\n")

    config_path = Path(__file__).parent.parent / "config" / "coordinates.json"

    # 确保config目录存在
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果配置文件不存在，创建默认配置
    if not config_path.exists():
        print("配置文件不存在，正在创建默认配置...\n")
        config = {
            "windows": {
                "article_list": {
                    "article_click_area": {"x": 0, "y": 0, "description": "文章点击位置"},
                    "row_height": 0,
                    "scroll_amount": 3,
                    "visible_articles": 5
                },
                "browser": {
                    "more_button": {"x": 0, "y": 0, "description": "更多按钮"},
                    "copy_link_menu": {"x": 0, "y": 0, "description": "复制链接菜单"},
                    "first_tab": {"x": 0, "y": 0, "description": "第一个标签"},
                    "close_tab_button": {"x": 0, "y": 0, "description": "关闭标签按钮"}
                }
            },
            "timing": {
                "click_interval": 0.3,
                "page_load_wait": 10.0,
                "menu_open_wait": 0.5
            },
            "collection": {
                "max_articles": 1000
            }
        }
    else:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

    # 校准公众号窗口
    print("--- 公众号窗口 ---")
    print("准备：请先点击【文章分组】按钮，并滚动到页面最顶部\n")

    # 测量行高
    print("--- 测量文章行高 ---")
    input("1. 将鼠标移动到【任意一篇文章的顶部】，按回车...")
    pos1 = get_mouse_position()
    print(f"   文章顶部: ({pos1.x}, {pos1.y})")

    input("   将鼠标移动到【下一篇文章的顶部】，按回车...")
    pos2 = get_mouse_position()
    print(f"   下一篇顶部: ({pos2.x}, {pos2.y})")

    row_height = abs(pos2.y - pos1.y)
    print(f"   已计算行高: {row_height} 像素\n")

    # 获取第一篇文章底部
    print("--- 获取第一篇文章底部 ---")
    input("2. 将鼠标移动到【第一篇文章的底部】，按回车...")
    pos_bottom = get_mouse_position()
    print(f"   第一篇底部: ({pos_bottom.x}, {pos_bottom.y})")

    # 计算点击位置（第一篇文章中间）
    click_y = pos_bottom.y - row_height // 2
    config['windows']['article_list']['article_click_area'] = {
        "x": pos_bottom.x, "y": click_y, "description": "文章点击位置（自动计算）"
    }
    config['windows']['article_list']['row_height'] = row_height
    
    
    # 测试滚动单位对应的像素
    print("--- 测试滚动单位 ---")
    print("将测量1个滚动单位对应多少像素\n")
    print("操作说明：")
    print("1. 将鼠标移动到文章列表区域内的参考点（如某篇文章的标题开头）")
    print("2. 记录参考点位置，然后在该位置执行1单位滚动")
    print("3. 滚动后，再次定位到同一参考点")
    print("4. 计算位置差值即为1单位对应的像素\n")

    input("将鼠标移动到文章列表区域内的参考点，按回车...")
    pos_before = get_mouse_position()
    print(f"   初始位置: ({pos_before.x}, {pos_before.y})")

    print("   将执行1单位滚动...")
    time.sleep(0.5)
    pyautogui.scroll(-1)
    time.sleep(1)

    input("   将鼠标移动到同一参考点（滚动后），按回车...")
    pos_after = get_mouse_position()
    print(f"   滚动后位置: ({pos_after.x}, {pos_after.y})")

    pixels_per_unit = abs(pos_after.y - pos_before.y)
    print(f"\n   1个滚动单位 = {pixels_per_unit} 像素")
    print(f"   行高 = {row_height} 像素")

    # 计算最佳滚动单位
    optimal_units = round(row_height / pixels_per_unit) if pixels_per_unit > 0 else 3
    print(f"   行高 {row_height} 像素 / {pixels_per_unit} 像素/单位 = {optimal_units} 单位")

    confirm = input(f"   建议使用 {optimal_units} 个滚动单位，是否接受？(y/n): ").strip().lower()
    if confirm == 'y':
        scroll_amount = optimal_units
    else:
        manual = input("   输入自定义滚动单位: ").strip()
        scroll_amount = int(manual) if manual else optimal_units
    
    config["windows"]["article_list"]["scroll_amount"] = scroll_amount
    print(f"   已记录滚动单位: {scroll_amount}\n")
    print(f"   已计算点击位置: ({pos_bottom.x}, {click_y})\n")
    # 获取窗口可见文章数（用于估计剩余文章）
    visible_count = input("3. 输入窗口可见文章数量（用于最后处理剩余文章，如5）: ").strip()
    config['windows']['article_list']['visible_articles'] = int(visible_count) if visible_count else 5
    print(f"   已记录: {config['windows']['article_list']['visible_articles']} 篇\n")

    # 校准浏览器窗口
    print("--- 微信内置浏览器窗口 ---")
    input("4. 将鼠标移动到【右上角更多按钮】上，按回车...")
    pos = get_mouse_position()
    config['windows']['browser']['more_button'] = {
        "x": pos.x, "y": pos.y, "description": "右上角更多按钮"
    }
    print(f"   已记录: ({pos.x}, {pos.y})\n")

    # 使用倒计时获取复制链接位置
    print("5. 获取【复制链接菜单项】位置")
    print("   准备：点击更多按钮后，窗口焦点会跳转")
    print("   操作：按回车后，10秒内完成以下步骤：")
    print("        1) 点击更多按钮")
    print("        2) 将鼠标移动到复制链接菜单项上")
    input("   准备好后按回车开始倒计时...")

    for i in range(10, 0, -1):
        print(f"   {i}秒...")
        time.sleep(1)

    pos = get_mouse_position()
    config['windows']['browser']['copy_link_menu'] = {
        "x": pos.x, "y": pos.y, "description": "复制链接菜单项"
    }
    print(f"   已记录: ({pos.x}, {pos.y})\n")

    # 校准标签管理位置
    print("--- 标签管理（防止浏览器崩溃）---")
    print("需要先打开20个标签以获取实际标签位置")
    input("6. 准备好后按回车，将自动点击文章20次...")

    print("   自动点击中...")
    click_x = config['windows']['article_list']['article_click_area']['x']
    click_y = config['windows']['article_list']['article_click_area']['y']

    for i in range(20):
        pyautogui.click(click_x, click_y)
        print(f"   已点击 {i+1}/20")
        time.sleep(2)

    print("   ✓ 已打开20个标签\n")

    input("7. 将鼠标移动到【第一个标签】上，按回车...")
    pos = get_mouse_position()
    config['windows']['browser']['first_tab'] = {
        "x": pos.x, "y": pos.y, "description": "第一个标签位置"
    }
    print(f"   已记录: ({pos.x}, {pos.y})\n")

    input("8. 将鼠标移动到【标签关闭按钮】上，按回车...")
    pos = get_mouse_position()
    config['windows']['browser']['close_tab_button'] = {
        "x": pos.x, "y": pos.y, "description": "标签关闭按钮"
    }
    print(f"   已记录: ({pos.x}, {pos.y})\n")

    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✓ 坐标配置已保存到: {config_path}")
    print("\n校准完成！")
    print("提示：可以运行 'python main.py test' 测试校准结果")

if __name__ == "__main__":
    calibrate()

def test_calibration():
    """测试校准结果"""
    print("\n=== 测试校准结果 ===\n")
    
    config_path = Path(__file__).parent.parent / "config" / "coordinates.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 测试文章点击位置
    print("--- 测试文章点击位置 ---")
    click_area = config['windows']['article_list']['article_click_area']
    print(f"将移动鼠标到文章点击位置: ({click_area['x']}, {click_area['y']})")
    input("按回车开始...")
    
    pyautogui.moveTo(click_area['x'], click_area['y'], duration=1)
    confirm = input("鼠标位置是否在第一篇文章中间？(y/n): ").strip().lower()
    if confirm != 'y':
        print("  ⚠ 位置不准确，建议重新校准")
        return False
    print("  ✓ 位置正确\n")
    
    # 测试滚动
    print("--- 测试滚动功能 ---")
    scroll_amount = config['windows']['article_list']['scroll_amount']
    print(f"将滚动 {scroll_amount} 像素")
    input("按回车开始...")
    
    pyautogui.moveTo(click_area['x'], click_area['y'])
    pyautogui.scroll(-scroll_amount)
    confirm = input("滚动距离是否正好一行？(y/n): ").strip().lower()
    if confirm != 'y':
        print("  ⚠ 滚动距离不准确，建议重新校准")
        return False
    print("  ✓ 滚动正确\n")
    
    # 测试更多按钮
    print("--- 测试更多按钮位置 ---")
    more_btn = config['windows']['browser']['more_button']
    print(f"将移动鼠标到更多按钮: ({more_btn['x']}, {more_btn['y']})")
    input("按回车开始...")
    
    pyautogui.moveTo(more_btn['x'], more_btn['y'], duration=1)
    confirm = input("鼠标位置是否在更多按钮上？(y/n): ").strip().lower()
    if confirm != 'y':
        print("  ⚠ 位置不准确，建议重新校准")
        return False
    print("  ✓ 位置正确\n")

    # 测试复制链接菜单位置
    print("--- 测试复制链接菜单位置 ---")
    copy_menu = config['windows']['browser']['copy_link_menu']
    print(f"将测试复制链接菜单位置: ({copy_menu['x']}, {copy_menu['y']})")
    print("操作：先点击更多按钮，然后移动鼠标到复制链接菜单项")
    input("按回车开始...")

    pyautogui.moveTo(more_btn['x'], more_btn['y'], duration=1)
    pyautogui.click()
    time.sleep(0.5)

    pyautogui.moveTo(copy_menu['x'], copy_menu['y'], duration=1)
    confirm = input("鼠标位置是否在复制链接菜单项上？(y/n): ").strip().lower()
    if confirm != 'y':
        print("  ⚠ 位置不准确，建议重新校准")
        return False
    print("  ✓ 位置正确\n")

    # 测试标签关闭功能
    print("--- 测试标签关闭功能 ---")
    first_tab = config['windows']['browser']['first_tab']
    close_btn = config['windows']['browser']['close_tab_button']
    print("将测试标签关闭功能（先打开3个标签，然后测试关闭）")
    input("按回车开始...")

    # 打开3个标签用于测试
    print("  打开3个测试标签...")
    for i in range(3):
        pyautogui.click(click_area['x'], click_area['y'])
        print(f"  已打开 {i+1}/3")
        time.sleep(2)

    # 测试点击第一个标签
    print(f"\n  测试点击第一个标签: ({first_tab['x']}, {first_tab['y']})")
    pyautogui.moveTo(first_tab['x'], first_tab['y'], duration=1)
    confirm = input("  鼠标是否在第一个标签上？(y/n): ").strip().lower()
    if confirm != 'y':
        print("  ⚠ 位置不准确，建议重新校准")
        return False

    # 显式点击第一个标签以激活当前标签页，再进行关闭按钮测试
    pyautogui.click(first_tab['x'], first_tab['y'])
    time.sleep(0.5)

    # 测试点击关闭按钮
    print(f"\n  测试点击关闭按钮: ({close_btn['x']}, {close_btn['y']})")
    pyautogui.moveTo(close_btn['x'], close_btn['y'], duration=1)
    confirm = input("  鼠标是否在关闭按钮上？(y/n): ").strip().lower()
    if confirm != 'y':
        print("  ⚠ 位置不准确，建议重新校准")
        return False

    # 关闭2个标签
    for i in range(2):
        pyautogui.click(close_btn['x'], close_btn['y'])
        time.sleep(0.3)

    confirm = input("  标签是否正确关闭？(y/n): ").strip().lower()
    if confirm != 'y':
        print("  ⚠ 标签关闭功能异常，建议重新校准")
        return False
    print("  ✓ 标签关闭正确\n")

    print("=" * 60)
    print("✓ 所有测试通过！可以开始采集了。")
    return True
