redis_sim={}
db_sim=[]

def reserve_seat(seat_id,student_id):
    if seat_id in redis_sim:
        print("同一个座位，失败了")
    else:
        redis_sim[seat_id]=student_id
        if seat_id in db_sim:  
            del redis_sim[seat_id]
            print("已经被别人预约过啦")
        else:
            db_sim.append(seat_id)
            print("恭喜你抢到座位了")

reserve_seat(1,100)
reserve_seat(2,200)
reserve_seat(1,300)
reserve_seat(1,400)

print("redis_sim:",redis_sim)
print("db_sim:",db_sim)