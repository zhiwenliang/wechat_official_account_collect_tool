"""
测试脚本 - 阶段1功能测试
"""
import pyautogui
import pyperclip
import time

def test_mouse_position():
    """测试鼠标位置获取"""
    print("=== 测试鼠标位置获取 ===")
    print("移动鼠标，5秒后显示位置...")
    time.sleep(5)
    pos = pyautogui.position()
    print(f"当前鼠标位置: ({pos.x}, {pos.y})")

def test_clipboard():
    """测试剪贴板操作"""
    print("\n=== 测试剪贴板 ===")
    test_text = "https://mp.weixin.qq.com/s/test123"
    pyperclip.copy(test_text)
    result = pyperclip.paste()
    print(f"写入: {test_text}")
    print(f"读取: {result}")
    print(f"测试{'成功' if result == test_text else '失败'}")

def test_click():
    """测试点击功能"""
    print("\n=== 测试点击功能 ===")
    print("5秒后将在当前鼠标位置点击...")
    time.sleep(5)
    pos = pyautogui.position()
    print(f"点击位置: ({pos.x}, {pos.y})")
    pyautogui.click(pos.x, pos.y)
    print("点击完成")

if __name__ == "__main__":
    print("选择测试项：")
    print("1. 测试鼠标位置")
    print("2. 测试剪贴板")
    print("3. 测试点击")

    choice = input("输入选项 (1/2/3): ")

    if choice == "1":
        test_mouse_position()
    elif choice == "2":
        test_clipboard()
    elif choice == "3":
        test_click()
    else:
        print("无效选项")
