records = {}         # 座位号 -> {"student", "status", "end_time"}
credit = {}          # 学生号 -> 分数
student_count = {}   # 学生号 -> 数量


def reserve(seat_id, student_id):
    if not (1 <= seat_id <= 10):
        return "座位号不存在"
    
    if credit.get(student_id,100) < 80:
        return "信用分不足，暂时不能预约"
         
    if student_count.get(student_id, 0) >= 3:
        return "今日预约已达上限"
        
    if seat_id in records:
        return "该座位已被预约"
         
    records[seat_id] = {
        "student": student_id,
        "status": "待签到",
        "end_time": "12:00"
    }
    student_count[student_id] = student_count.get(student_id, 0) + 1
    return "预约成功" 
    
    
    
def cancel(seat_id, student_id):
    if seat_id not in records:
        return "这个座位当前没有被预约"
    if student_id != records[seat_id]["student"]:
        return "这不是你的预约"
    
    del records[seat_id]
    student_count[student_id] = student_count.get(student_id , 0) - 1
    credit[student_id] = credit.get(student_id , 100 )-2
    print(f"学生{student_id}信用分 -2，当前{credit[student_id]}分")
    print(f"座位 {seat_id} 已从第 {student_id} 号学生名下释放")
    return "取消成功"
    
    
def checkin(seat_id, student_id):
    if seat_id not in records:
        return "这个座位当前没有被预约"
    if student_id != records[seat_id]["student"]:
        return "这不是你的预约"
    if records[seat_id]["status"] =="已签到":
        return "已签到，请勿重复操作"
    if records[seat_id]["status"] =="待签到":
        records[seat_id]["status"] ="已签到"
        return "签到成功"
    return "当前状态不能签到"
    
    
def auto_checkout(current_time):
    count=0
    for seat_id,info in records.items():
        if info["status"] == "已签到":
            if info["end_time"] < current_time:
                info["status"] = "已完成"
                print(f"自动签退:{seat_id},学生{info['student']}")
                count+=1
    return count
    
def show_status():
    for seat_id,info in records.items():
        print(f"座位{seat_id}-->学生{info['student']}({info['status']},结束{info['end_time']})")
    print(f"一共{len(records)}条信息")
    
print("=== 1. 正常预约 ===")
print(reserve(1, 100))
print(reserve(2, 100))
print(reserve(3, 200))

print("=== 2. 座位被占 ===")
print(reserve(1, 300))
print(reserve(1, 400))

print("=== 3. 边界测试 ===")
print(reserve(11, 500))    # 座位号不存在
print(reserve(4, 100))     # 第 3 个，成功
print(reserve(5, 100))     # 第 4 个，超限

print("=== 4. 当前数据 ===")
print("records:", records)
print("student_count:", student_count)

print("=== 签到测试 ===")
print(checkin(1, 100))     # 签到成功
print(checkin(1, 100))     # 已签到，请勿重复操作
print(checkin(1, 200))     # 这不是你的预约
print(checkin(9, 100))     # 这个座位当前没有被预约


print("=== 自动签退测试 ===")
# 此时座位 1 是"已签到"，座位 2/3/4 是"待签到"
print(f"自动签退 11:00 → 处理 {auto_checkout('11:00')} 条")   # 0 条（12:00 > 11:00）
print(f"自动签退 13:00 → 处理 {auto_checkout('13:00')} 条")   # 1 条（座位 1）
print(f"再跑一次 13:00 → 处理 {auto_checkout('13:00')} 条")   # 0 条（已经完成了）
print("records:", records)
show_status()

print(cancel(1, 999))
print(cancel(9, 100))
print(cancel(1, 100))





    
