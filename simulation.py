"""
超简化外卖流水线仿真系统
包含完整的仿真逻辑、异常处理和数据收集
"""

import simpy
import random
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import time

# 配置参数
SIMULATION_TIME = 120  # 仿真时长（分钟）
ORDER_RATE = 2.0      # 每分钟订单数
MERCHANT_COUNT = 10    # 商家数量
RIDER_COUNT = 30       # 骑手数量
MERCHANT_CAPACITY = 4 # 商家容量

# 时间参数（分钟）
COOKING_TIME = (8, 15)    # 备餐时间范围
DELIVERY_TIME = (12, 20)  # 配送时间范围
PICKUP_TIME = 2           # 取餐时间

# 异常参数
EXCEPTION_RATE = 0.1     # 异常发生率
RETRY_LIMIT = 2           # 最大重试次数

class OrderStatus(Enum):
    CREATED = "已创建"
    COOKING = "备餐中"
    READY = "待取餐"
    DELIVERING = "配送中"
    DELIVERED = "已送达"
    FAILED = "失败"

@dataclass
class Order:
    """订单类"""
    id: str
    merchant_id: str
    status: OrderStatus = OrderStatus.CREATED
    created_time: float = 0
    cooking_start: Optional[float] = None
    ready_time: Optional[float] = None
    pickup_time: Optional[float] = None
    delivered_time: Optional[float] = None
    
    # 异常处理
    retry_count: int = 0
    total_delay: float = 0
    exceptions: List[str] = field(default_factory=list)
    
    # 理想时间（用于对比）
    ideal_cooking_time: float = 10
    ideal_delivery_time: float = 15
    
    def get_total_time(self) -> Optional[float]:
        if self.delivered_time:
            return self.delivered_time - self.created_time
        return None
    
    def get_ideal_time(self) -> float:
        return self.ideal_cooking_time + PICKUP_TIME + self.ideal_delivery_time


@dataclass
class Resource:
    """资源类（商家或骑手）"""
    id: str
    name: str
    busy: bool = False
    current_orders: List[str] = field(default_factory=list)
    total_processed: int = 0

class DeliveryPipeline:
    """外卖流水线仿真系统"""
    
    def __init__(self):
        self.env = simpy.Environment()
        
        # 资源
        self.merchants = [Resource(f"M{i+1}", f"商家{i+1}") for i in range(MERCHANT_COUNT)]
        self.riders = [Resource(f"R{i+1}", f"骑手{i+1}") for i in range(RIDER_COUNT)]
        
        # 数据存储
        self.orders = []
        self.order_counter = 0
        self.pipeline_data = []  # 流水线状态数据
        
        # 统计
        self.stats = {
            'total_orders': 0,
            'completed_orders': 0,
            'failed_orders': 0,
            'total_delay': 0,
            'total_exceptions': 0,
            'avg_actual_time': 0,
            'avg_ideal_time': 0,
            'efficiency': 0
        }
        
        random.seed(42)
        np.random.seed(42)
    
    def create_order(self) -> Order:
        """创建新订单"""
        self.order_counter += 1
        merchant = random.choice(self.merchants)
        
        order = Order(
            id=f"O{self.order_counter:03d}",
            merchant_id=merchant.id,
            created_time=self.env.now,
            ideal_cooking_time=random.uniform(*COOKING_TIME),
            ideal_delivery_time=random.uniform(*DELIVERY_TIME)
        )
        
        self.orders.append(order)
        self.stats['total_orders'] += 1
        return order
    
    def find_available_merchant(self, merchant_id: str) -> Optional[Resource]:
        """查找可用商家"""
        merchant = next((m for m in self.merchants if m.id == merchant_id), None)
        if merchant and len(merchant.current_orders) < MERCHANT_CAPACITY:
            return merchant
        return None
    
    def find_available_rider(self) -> Optional[Resource]:
        """查找可用骑手"""
        available = [r for r in self.riders if not r.busy]
        return random.choice(available) if available else None
    
    def record_pipeline_state(self, order: Order, stage: str, details: str = ""):
        """记录流水线状态"""
        self.pipeline_data.append({
            'time': self.env.now,
            'order_id': order.id,
            'stage': stage,
            'status': order.status.value,
            'details': details,
            'retry_count': order.retry_count,
            'total_delay': order.total_delay
        })
    
    def handle_exception(self, order: Order, stage: str) -> bool:
        """处理异常，返回是否应该重试"""
        if random.random() > EXCEPTION_RATE:
            return False  # 没有异常
        
        exception_types = {
            'cooking': ['设备故障', '食材不足', '人员忙碌'],
            'delivery': ['交通堵塞', '地址错误', '客户不在']
        }
        
        exception = random.choice(exception_types.get(stage, ['未知异常']))
        order.exceptions.append(f"{stage}:{exception}")
        self.stats['total_exceptions'] += 1
        
        # 计算延迟时间
        if stage == 'cooking':
            delay = random.uniform(3, 15)
        else:  # delivery
            delay = random.uniform(5, 25)
        
        order.total_delay += delay
        order.retry_count += 1
        
        self.record_pipeline_state(order, stage, f"异常:{exception},延迟{delay:.1f}分钟")
        
        # 决定是否重试
        if order.retry_count >= RETRY_LIMIT:
            order.status = OrderStatus.FAILED
            self.stats['failed_orders'] += 1
            self.record_pipeline_state(order, stage, f"重试次数超限,订单失败")
            return False
        
        return True  # 重试
    
    def order_generation_process(self):
        """订单生成过程"""
        while True:
            interval = np.random.exponential(1.0 / ORDER_RATE)
            yield self.env.timeout(interval)
            
            order = self.create_order()
            self.record_pipeline_state(order, "创建", "新订单生成")
            self.env.process(self.order_pipeline(order))
    
    def order_pipeline(self, order: Order):
        """订单流水线处理"""
        try:
            # 阶段1：商家处理
            yield self.env.process(self.merchant_stage(order))
            if order.status == OrderStatus.FAILED:
                return
            
            # 阶段2：骑手配送
            yield self.env.process(self.delivery_stage(order))
            
        except Exception as e:
            order.status = OrderStatus.FAILED
            self.stats['failed_orders'] += 1
            self.record_pipeline_state(order, "系统", f"系统错误:{e}")
    
    def merchant_stage(self, order: Order):
        """商家处理阶段"""
        while order.retry_count < RETRY_LIMIT:
            # 等待商家可用
            while True:
                merchant = self.find_available_merchant(order.merchant_id)
                if merchant:
                    break
                yield self.env.timeout(1)  # 等待1分钟
            
            # 商家接单
            merchant.current_orders.append(order.id)
            order.status = OrderStatus.COOKING
            order.cooking_start = self.env.now
            self.record_pipeline_state(order, "接单", f"商家{merchant.id}开始处理")
            
            # 备餐过程
            cooking_time = order.ideal_cooking_time
            
            # 检查异常
            if self.handle_exception(order, 'cooking'):
                # 有异常但要重试
                cooking_time += order.total_delay
                yield self.env.timeout(cooking_time)
                merchant.current_orders.remove(order.id)
                continue  # 重试
            elif order.status == OrderStatus.FAILED:
                # 异常且不重试
                merchant.current_orders.remove(order.id)
                return
            
            # 正常完成备餐
            yield self.env.timeout(cooking_time)
            order.status = OrderStatus.READY
            order.ready_time = self.env.now
            merchant.current_orders.remove(order.id)
            merchant.total_processed += 1
            
            self.record_pipeline_state(order, "备餐完成", f"用时{cooking_time:.1f}分钟")
            break
    
    def delivery_stage(self, order: Order):
        """配送阶段"""
        while order.retry_count < RETRY_LIMIT:
            # 等待骑手可用
            while True:
                rider = self.find_available_rider()
                if rider:
                    break
                yield self.env.timeout(1)
            
            # 骑手接单
            rider.busy = True
            rider.current_orders.append(order.id)
            self.record_pipeline_state(order, "分配骑手", f"骑手{rider.id}接单")
            
            # 取餐
            yield self.env.timeout(PICKUP_TIME)
            order.pickup_time = self.env.now
            order.status = OrderStatus.DELIVERING
            self.record_pipeline_state(order, "开始配送", "骑手取餐完成")
            
            # 配送过程
            delivery_time = order.ideal_delivery_time
            
            # 检查异常
            if self.handle_exception(order, 'delivery'):
                # 有异常但要重试
                delivery_time += order.total_delay
                yield self.env.timeout(delivery_time)
                rider.busy = False
                rider.current_orders.remove(order.id)
                order.status = OrderStatus.READY  # 回到待配送状态
                continue  # 重新分配骑手
            elif order.status == OrderStatus.FAILED:
                # 异常且不重试
                rider.busy = False
                rider.current_orders.remove(order.id)
                return
            
            # 正常完成配送
            yield self.env.timeout(delivery_time)
            order.status = OrderStatus.DELIVERED
            order.delivered_time = self.env.now
            rider.busy = False
            rider.current_orders.remove(order.id)
            rider.total_processed += 1
            
            self.stats['completed_orders'] += 1
            self.record_pipeline_state(order, "配送完成", f"总用时{order.get_total_time():.1f}分钟")
            break
    
    def statistics_process(self):
        """统计更新过程"""
        while True:
            yield self.env.timeout(10)  # 每10分钟更新
            self.update_statistics()
    
    def update_statistics(self):
        """更新统计信息"""
        completed = [o for o in self.orders if o.status == OrderStatus.DELIVERED]
        
        if completed:
            actual_times = [o.get_total_time() for o in completed]
            ideal_times = [o.get_ideal_time() for o in completed]
            
            self.stats['avg_actual_time'] = np.mean(actual_times)
            self.stats['avg_ideal_time'] = np.mean(ideal_times)
            self.stats['efficiency'] = self.stats['avg_ideal_time'] / self.stats['avg_actual_time']
            self.stats['total_delay'] = sum(o.total_delay for o in self.orders)
    
    def get_results(self):
        """获取仿真结果"""
        completed_orders = [o for o in self.orders if o.status == OrderStatus.DELIVERED]
        
        results = {
            'summary': {
                'total_orders': self.stats['total_orders'],
                'completed_orders': self.stats['completed_orders'],
                'failed_orders': self.stats['failed_orders'],
                'completion_rate': self.stats['completed_orders'] / max(1, self.stats['total_orders']),
                'avg_actual_time': self.stats['avg_actual_time'],
                'avg_ideal_time': self.stats['avg_ideal_time'],
                'efficiency': self.stats['efficiency'],
                'total_exceptions': self.stats['total_exceptions'],
                'total_delay': self.stats['total_delay']
            },
            'orders': self.orders,
            'pipeline_data': self.pipeline_data,
            'resources': {
                'merchants': self.merchants,
                'riders': self.riders
            }
        }
        
        return results

    def run(self, duration: int = SIMULATION_TIME):
        """测试仿真"""
        print(f"开始仿真 - 时长: {duration}分钟")
        print(f"配置: {MERCHANT_COUNT}个商家, {RIDER_COUNT}个骑手")
        print("-" * 50)

        # 启动进程
        self.env.process(self.order_generation_process())
        self.env.process(self.statistics_process())

        # 运行仿真
        self.env.run(until=duration)

        # 最终统计
        self.update_statistics()

        print("仿真完成!")
        return self.get_results()

# 测试运行
if __name__ == "__main__":
    sim = DeliveryPipeline()
    results = sim.run(30)
    
    print("\n=== 仿真结果 ===")
    summary = results['summary']
    print(f"总订单: {summary['total_orders']}")
    print(f"完成订单: {summary['completed_orders']}")
    print(f"失败订单: {summary['failed_orders']}")
    print(f"完成率: {summary['completion_rate']:.2%}")
    print(f"平均实际时间: {summary['avg_actual_time']:.1f}分钟")
    print(f"平均理想时间: {summary['avg_ideal_time']:.1f}分钟")
    print(f"效率: {summary['efficiency']:.2%}")
    print(f"总异常数: {summary['total_exceptions']}")
    print(f"总延迟: {summary['total_delay']:.1f}分钟")

