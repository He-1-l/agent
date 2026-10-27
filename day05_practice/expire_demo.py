reservations = [
    {"id": 1, "student_id": 101, "status": 0, "is_active": 1, "deadline": "10:00"},
    {"id": 2, "student_id": 102, "status": 0, "is_active": 1, "deadline": "11:00"},
    {"id": 3, "student_id": 103, "status": 0, "is_active": 1, "deadline": "20:00"},
    {"id": 4, "student_id": 104, "status": 1, "is_active": 1, "deadline": "09:00"},
]

now = "12:00"
count=0
for i in reservations:
    if i["status"] == 0 and i["is_active"] == 1 and i["deadline"] < now:
        i["status"]=4
        i["is_active"]=None
        print(f"释放座位：预约{i['id']}(学生{i['student_id']},截止{i['deadline']})")
        count+=1
print(f"共释放{count}个座位")