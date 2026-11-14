# 外卖平台订单流程流水线仿真系统帮助文档

---

## 项目概述

本项目基于SimPy离散事件仿真框架，实现了一个完整的外卖平台订单处理流水线仿真系统。项目的核心目标是通过仿真建模来分析外卖订单处理流程中的性能瓶颈，并提供可视化的分析工具来对比实际运行结果与理论最优结果。

<img src=".\result_demo\pipeline_flow.png" alt="pipeline_flow" />

### 核心特性

1. **完整的流水线建模**：从订单生成到最终配送完成的全流程仿真
2. **智能异常处理**：基于重新调度机制而非简单取消的异常处理策略
3. **理想模式对比**：实际运行时间与理论最优时间的对比分析
4. **流水线可视化**：订单在各个阶段的状态可视化展示
5. **性能指标分析**：多维度的系统性能评估指标

### 流水线架构

```
订单生成 → 商家接单 → 备餐处理 → 骑手取餐 → 配送完成
```

### 目录结构

```python
simpy_pipeline/                    # 项目根目录
├── main.py                        # 主程序入口文件 (167行)
├── simulation.py                  # 核心仿真引擎 (385行)
├── visualization.py               # 可视化分析模块 (415行)
├── README.md                      # 项目说明文档
└── results_YYYYMMDD_HHMMSS/      # 运行结果目录 (自动生成)
    ├── pipeline_flow.png          # 流水线流程图
    ├── dashboard.png              # 综合仪表板
    └── report.txt                 # 简洁报告
```

---





## 项目部署方法

### 环境要求

- **Python版本**：3.7 或更高版本

```bash
pip install simpy numpy matplotlib pandas seaborn
```

### 快速运行测试

```bash
# 直接运行测试
python main.py

# 手动设置参数进行测试（模拟时长，是否生成可视化结果图）
python main.py --duration 120 --no-viz
```



## 代码文件详述

### 1. simulation.py - 核心仿真引擎

这是项目的核心文件，包含了完整的仿真逻辑实现。

#### 1.1 配置参数部分

```python
# 配置参数
SIMULATION_TIME = 120  # 仿真时长（分钟）
ORDER_RATE = 2.0      # 每分钟订单数
MERCHANT_COUNT = 10   # 商家数量
RIDER_COUNT = 30      # 骑手数量
MERCHANT_CAPACITY = 4  # 商家容量（最多同时服务的客户数量）

# 时间参数（分钟）
COOKING_TIME = (8, 15)    # 备餐时间范围
DELIVERY_TIME = (12, 20)  # 配送时间范围
PICKUP_TIME = 2           # 取餐时间

# 异常参数
EXCEPTION_RATE = 0.1     # 异常发生率
RETRY_LIMIT = 2          # 最大重试次数
```

**设计思路**：
- `ORDER_RATE`：基于泊松分布的订单到达率，模拟真实的随机订单生成
- `MERCHANT_CAPACITY`：每个商家的并发处理能力，模拟真实的厨房容量限制
- `EXCEPTION_RATE`：异常发生概率，模拟真实环境中的各种不确定因素
- `RETRY_LIMIT`：重试机制的上限，避免无限重试导致的系统阻塞

#### 1.2 数据模型设计

```python
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
    
    # 异常处理相关
    retry_count: int = 0
    total_delay: float = 0
    exceptions: List[str] = field(default_factory=list)
    
    # 理想时间（用于对比）
    ideal_cooking_time: float = 10
    ideal_delivery_time: float = 15
```

**设计亮点**：
1. **完整的时间跟踪**：记录订单在每个阶段的时间戳，便于后续分析
2. **异常信息记录**：保存异常类型和重试次数，用于异常分析
3. **理想时间对比**：存储理论最优时间，用于效率计算

#### 1.3 核心仿真逻辑

**订单生成过程**：
```python
def order_generation_process(self):
    """订单生成过程"""
    while True:
        interval = np.random.exponential(1.0 / ORDER_RATE)
        yield self.env.timeout(interval)
        
        order = self.create_order()
        self.record_pipeline_state(order, "创建", "新订单生成")
        self.env.process(self.order_pipeline(order))
```

**设计思路**：
- 使用指数分布生成订单间隔，符合泊松过程的特性
- 每个订单独立启动一个处理流程，实现并发处理

**异常处理机制**：
```python
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
    
    # 计算延迟时间
    if stage == 'cooking':
        delay = random.uniform(5, 15)
    else:  # delivery
        delay = random.uniform(10, 25)
    
    order.total_delay += delay
    order.retry_count += 1
    
    # 决定是否重试
    if order.retry_count >= RETRY_LIMIT:
        order.status = OrderStatus.FAILED
        return False
    
    return True  # 重试
```

**创新点**：
1. **分阶段异常类型**：不同阶段有不同的异常类型，更贴近现实
2. **累计延迟跟踪**：记录每次异常造成的延迟，用于性能分析
3. **智能重试机制**：避免直接取消，通过重新调度提高成功率

### 2. visualization.py - 流水线可视化模块

这个文件实现了丰富的可视化功能，是项目的重要组成部分。

#### 2.1 流水线流程图实现

```python
def _plot_order_timeline(self, ax):
    """绘制订单状态时间线"""
    completed_orders = [o for o in self.orders if o.status.value in ['已送达', '失败']][:20]
    
    for order in completed_orders:
        # 绘制各阶段时间条
        stages = []
        if order.cooking_start:
            stages.append(('创建', start_time, order.cooking_start, self.colors['已创建']))
        if order.ready_time:
            stages.append(('备餐', order.cooking_start, order.ready_time, self.colors['备餐中']))
        # ... 其他阶段
        
        # 绘制异常标记
        order_exceptions = [d for d in self.pipeline_data if d['order_id'] == order.id and '异常' in d['details']]
        for exc in order_exceptions:
            ax.scatter(exc['time'], y_pos, c=self.colors['异常'], s=50, marker='x', zorder=4)
```

**可视化特点**：
1. **时间轴展示**：横轴为时间，纵轴为不同订单，直观显示处理流程
2. **颜色编码**：不同阶段使用不同颜色，便于识别
3. **异常标记**：用特殊符号标记异常发生的时间点
4. **延迟信息**：显示每个订单的总时间和延迟时间

#### 2.2 实际vs理想对比图

```python
def _plot_actual_vs_ideal(self, ax):
    """绘制实际vs理想时间对比"""
    actual_times = [o.get_total_time() for o in completed_orders]
    ideal_times = [o.get_ideal_time() for o in completed_orders]
    delays = [o.total_delay for o in completed_orders]
    
    # 绘制柱状图
    bars1 = ax.bar(x - width/2, ideal_times, width, label='理想时间', color='#2ecc71')
    bars2 = ax.bar(x + width/2, actual_times, width, label='实际时间', color='#3498db')
    
    # 标记延迟部分
    for i, (actual, ideal, delay) in enumerate(zip(actual_times, ideal_times, delays)):
        if delay > 0:
            ax.bar(x[i] + width/2, delay, width, bottom=ideal, color='#e74c3c')
```

**设计亮点**：
1. **对比清晰**：理想时间和实际时间并排显示，差异一目了然
2. **延迟高亮**：用红色标记延迟部分，突出问题所在
3. **效率计算**：自动计算并显示系统效率指标

### 3. main.py - 主程序入口

这个文件整合了仿真和可视化功能，提供了用户友好的接口。

#### 3.1 命令行参数处理

```python
parser = argparse.ArgumentParser(description='外卖流水线仿真系统')
parser.add_argument('--duration', type=int, default=120, help='仿真时长（分钟）')
parser.add_argument('--no-viz', action='store_true', help='不显示可视化')
parser.add_argument('--output', type=str, default='results', help='输出目录前缀')
```



