# list = [[0]*3]*3
listTemp = [[0] * 3 for _ in range(3)]

listTemp[0][0] = 1


def useVariable():
    # list = [[0] * 3 for _ in range(3)]

    # 如果试图在内层函数中修改全局变量或嵌套变量，若不加声明，Python 会隐式地在当前作用域创建一个同名的新局部变量
    # global listTemp # 只是读取全局变量、或者修改可变对象（如列表、字典内部的元素），完全不需要加 global
    listTemp[0][1] = 2
    print("listTemp in useVariable: ", listTemp)


useVariable()

print(listTemp)
