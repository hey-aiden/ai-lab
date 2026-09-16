class Step:
    def __init__(self, name):
        self.name = name

    # __or__ 是运算符重载
    def __or__(self, other):
        return Step(f"{self.name} -> {other.name}")

    def __repr__(self):
        return f"Step({self.name!r})"  # f"{self.name}"，等价于 str(self.name)；对字符串来说，repr("abc") 是 "'abc'"（带引号），str("abc") 是 "abc"。所以输出里有单引号


a = Step("加载数据")
b = Step("清洗数据")
c = Step("训练模型")

# 先执行 a | b，等价于 a.__or__(b) -》 返回一个新的 Step 对象，name 为 "加载数据 -> 清洗数据"
# ab | c  -》  返回新的 Step，name 为 "加载数据 -> 清洗数据 -> 训练模型"
pipeline = a | b | c

# print(pipeline)  调用 pipeline.__repr__()  !r 表示用 repr() 而不是 str() 来格式化，所以字符串会带引号
print(pipeline)
