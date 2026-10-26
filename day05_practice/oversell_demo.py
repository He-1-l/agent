seats = list(range(1,11))
db_sim=[]

for i in range(50):
    seat = seats[i%10]
    db_sim.append(seat)
    
print(db_sim)

total_oversold = 0
for seat in seats:
    times = db_sim.count(seat)
    if times > 1:
        oversold = times - 1
        total_oversold= total_oversold + oversold
        print(f"座位{seat}被预约{times}次,超卖{oversold}次")
        
print(f"总超卖:{total_oversold}次")