"""
input() 函数接受一个标准输入数据，返回为 string 类型
"""


def listen_input():
    while True:
        user_prompt = input("你:").strip()  # strip: 截掉字符串左边的空格或指定字符
        if user_prompt in ("quit"):
            break
        print(user_prompt)


listen_input()
