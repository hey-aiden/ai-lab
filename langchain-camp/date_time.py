from datetime import date, datetime, time, timedelta

# 1. 当前日期 / 当前日期时间
print("今天日期:", date.today())
print("当前时间:", datetime.now())

# 2. 手动构造
d = date(2026, 9, 14)
t = time(14, 30, 0)
dt = datetime(2026, 9, 14, 14, 30, 0)
print("构造日期:", d)
print("构造时间:", t)
print("构造日期时间:", dt)

# 3. 取单个字段
print("年/月/日:", dt.year, dt.month, dt.day)
print("时/分/秒:", dt.hour, dt.minute, dt.second)

# 4. 格式化输出 strftime
print("格式化:", dt.strftime("%Y-%m-%d %H:%M:%S"))
print("中文格式:", dt.strftime("%Y年%m月%d日 %H时%M分"))

# 5. 从字符串解析 strptime
dt2 = datetime.strptime("2026-09-14 14:30", "%Y-%m-%d %H:%M")
print("解析字符串:", dt2)

# 6. 时间差 timedelta
tomorrow = date.today() + timedelta(days=1)
yesterday = date.today() - timedelta(days=1)
one_hour_later = datetime.now() + timedelta(hours=1)
print("明天:", tomorrow)
print("昨天:", yesterday)
print("一小时后:", one_hour_later)

# 7. 两个时间相减
delta = datetime.now() - dt2
print("距 dt2 过了:", delta.days, "天", delta.seconds, "秒")
