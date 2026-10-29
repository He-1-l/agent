# 预约状态机

## reservation.status  中数字代表的状态

| 值 | 含义  | 谁写入              |
| - | --- | ---------------- |
| 0 | 待签到 | reserve()        |
| 1 | 已签到 | checkin()        |
| 2 | 已完成 | checkout()       |
| 3 | 已取消 | cancel()         |
| 4 | 违约  | expire_no_show() |

## 状态转换

'''
0 --reserve()--> 1 --checkin() --> 2  
0 --cancel()--> 3  
0 --expire_no_show()-->4 --admin.py --> 3  
'''

### 终态：2(已完成)和3(已取消)

# 三个缺陷

1. checkin() 说“座位已释放”，其实有60秒的轮询，中间时间所有人无法预约
2. expire_no_show()的commit在循环外面，如果失败了会导致数据库和redis数据表不一致
3. cancel()取消功能没有扣分惩罚

## 其他表的status

- Students：1 正常 ，非1 禁用
- Seat：1=可用，0=维修
- Waitlist：0=排队 1=已补位 2=放弃 3=过期
