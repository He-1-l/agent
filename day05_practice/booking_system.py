student_sim={}
count_sim={}

def reserve(seat_id, student_id):
    # 1. 检查座位号合法
    if not (1 <= seat_id <= 10):
        return "座位号无效"

    # 2. 检查座位是否已被占
    if seat_id in student_sim:
        return "该座位已被预约"

    # 3. 检查这个学生今天约了几个
    if count_sim.get(student_id, 0) >= 3:
        return "今日预约已达上限"

    # 4. 记录
    student_sim[seat_id] = student_id
    count_sim[student_id] = count_sim.get(student_id, 0) + 1

    return "预约成功"
    
def cancel(seat_id,student_id):
    # 1. 判断座位是不是他的
    if student_sim.get(seat_id) != student_id:
        return "这不是你的预约"
    del student_sim[seat_id]
    count_sim[student_id] = count_sim.get(student_id,0) - 1
    return "取消成功"
    
def show_status():
    for seat, student in student_sim.items():
        print(f"座位{seat} --> 学生{student}")
        
print(reserve(1, 100))     # 预约成功
print(reserve(2, 100))     # 预约成功
print(reserve(3, 100))     # 预约成功
print(reserve(4, 100))     # 今日预约已达上限
print(reserve(1, 200))     # 该座位已被预约
print(cancel(1, 200))      # 这不是你的预约
print(cancel(1, 100))      # 取消成功
print(reserve(4, 100))     # 预约成功（取消后释放了名额）
show_status()