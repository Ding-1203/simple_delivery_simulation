"""
流水线可视化模块
实现订单流水线状态可视化和理想模式对比
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np
from typing import Dict, List
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class PipelineVisualizer:
    """流水线可视化器"""
    
    def __init__(self, results: Dict):
        self.results = results
        self.orders = results['orders']
        self.pipeline_data = results['pipeline_data']
        self.summary = results['summary']
        
        # 颜色配置
        self.colors = {
            '已创建': '#3498db',
            '备餐中': '#f39c12', 
            '待取餐': '#e67e22',
            '配送中': '#9b59b6',
            '已送达': '#2ecc71',
            '异常': '#ff6b6b'
        }
    
    def create_pipeline_flow_chart(self, save_path: str = None):
        """创建流水线流程图"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
        
        # 上半部分：订单状态时间线
        self._plot_order_timeline(ax1)
        
        # 下半部分：实际vs理想对比
        self._plot_actual_vs_ideal(ax2)
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def _plot_order_timeline(self, ax):
        """绘制订单状态时间线"""
        ax.set_title('订单流水线状态时间线', fontsize=14, fontweight='bold')
        
        # 获取已完成的订单
        completed_orders = [o for o in self.orders if o.status.value in ['已送达', '失败']][:20]  # 显示前20个
        
        if not completed_orders:
            ax.text(0.5, 0.5, '暂无完成的订单', ha='center', va='center', transform=ax.transAxes)
            return
        
        y_pos = 0
        for order in completed_orders:
            # 绘制订单流程条
            start_time = order.created_time
            
            # 各阶段时间点
            stages = []
            if order.cooking_start:
                stages.append(('创建', start_time, order.cooking_start, self.colors['已创建']))
            if order.ready_time:
                stages.append(('备餐', order.cooking_start or start_time, order.ready_time, self.colors['备餐中']))
            if order.pickup_time:
                stages.append(('等待', order.ready_time or start_time, order.pickup_time, self.colors['待取餐']))
            if order.delivered_time:
                stages.append(('配送', order.pickup_time or start_time, order.delivered_time, self.colors['配送中']))
                # 最终状态
                final_color = self.colors['已送达'] if order.status.value == '已送达' else self.colors['失败']
                ax.scatter(order.delivered_time, y_pos, c=final_color, s=100, zorder=3)
            
            # 绘制各阶段
            for stage_name, start, end, color in stages:
                duration = end - start
                rect = patches.Rectangle((start, y_pos-0.3), duration, 0.6, 
                                       facecolor=color, alpha=0.7, edgecolor='black')
                ax.add_patch(rect)
            
            # 标记异常
            order_exceptions = [d for d in self.pipeline_data if d['order_id'] == order.id and '异常' in d['details']]
            for exc in order_exceptions:
                ax.scatter(exc['time'], y_pos, c=self.colors['异常'], s=50, marker='x', zorder=4)
            
            # 订单标签
            ax.text(start_time-1, y_pos, order.id, ha='right', va='center', fontsize=8)
            
            # 显示总时间和延迟
            total_time = order.get_total_time() or 0
            ideal_time = order.get_ideal_time()
            delay = order.total_delay
            
            ax.text(order.delivered_time + 1 if order.delivered_time else start_time + 10, y_pos, 
                   f'{total_time:.1f}min (延迟:{delay:.1f})', ha='left', va='center', fontsize=8)
            
            y_pos += 1
        
        ax.set_xlabel('时间 (分钟)')
        ax.set_ylabel('订单')
        ax.set_ylim(-0.5, len(completed_orders) - 0.5)
        ax.grid(True, alpha=0.3)
        
        # 图例
        legend_elements = [patches.Patch(color=color, label=stage) 
                          for stage, color in self.colors.items() if stage != '异常' and stage != '已送达']
        legend_elements.append(
            plt.Line2D([0], [0], marker='o', color=self.colors['已送达'], linestyle='None',
                       markersize=8, label='已送达')
        )
        legend_elements.append(
            plt.Line2D([0], [0], marker='x', color=self.colors['异常'], linestyle='None',
                       markersize=8, label='异常')
        )
        ax.legend(handles=legend_elements, loc='upper right')
    
    def _plot_actual_vs_ideal(self, ax):
        """绘制实际vs理想时间对比"""
        ax.set_title('实际时间 vs 理想时间对比', fontsize=14, fontweight='bold')
        
        completed_orders = [o for o in self.orders if o.status.value == '已送达']
        
        if not completed_orders:
            ax.text(0.5, 0.5, '暂无完成的订单', ha='center', va='center', transform=ax.transAxes)
            return
        
        actual_times = [o.get_total_time() for o in completed_orders]
        ideal_times = [o.get_ideal_time() for o in completed_orders]
        delays = [o.total_delay for o in completed_orders]
        
        x = np.arange(len(completed_orders))
        width = 0.35
        
        # 绘制柱状图
        bars1 = ax.bar(x - width/2, ideal_times, width, label='理想时间', color='#2ecc71', alpha=0.7)
        bars2 = ax.bar(x + width/2, actual_times, width, label='实际时间', color='#3498db', alpha=0.7)
        
        # # 标记延迟部分
        # for i, (actual, ideal, delay) in enumerate(zip(actual_times, ideal_times, delays)):
        #     if delay > 0:
        #         ax.bar(x[i] + width/2, delay, width, bottom=ideal, color='#e74c3c', alpha=0.7)
        
        # 添加数值标签
        for i, (actual, ideal) in enumerate(zip(actual_times, ideal_times)):
            ax.text(x[i] - width/2, ideal + 0.5, f'{ideal:.1f}', ha='center', va='bottom', fontsize=8)
            ax.text(x[i] + width/2, actual + 0.5, f'{actual:.1f}', ha='center', va='bottom', fontsize=8)
        
        ax.set_xlabel('订单序号')
        ax.set_ylabel('时间 (分钟)')
        ax.set_xticks(x)
        ax.set_xticklabels([o.id for o in completed_orders], rotation=45)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 添加统计信息
        avg_actual = np.mean(actual_times)
        avg_ideal = np.mean(ideal_times)
        efficiency = avg_ideal / avg_actual * 100
        
        ax.text(0.02, 0.98, f'平均理想时间: {avg_ideal:.1f}分钟\n平均实际时间: {avg_actual:.1f}分钟\n效率: {efficiency:.1f}%', 
                transform=ax.transAxes, va='top', ha='left', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    def create_pipeline_dashboard(self, save_path: str = None):
        """创建流水线仪表板"""
        fig = plt.figure(figsize=(16, 12))
        
        # 创建网格布局
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. 总体统计
        ax1 = fig.add_subplot(gs[0, 0])
        self._plot_summary_stats(ax1)
        
        # 2. 完成率饼图
        ax2 = fig.add_subplot(gs[0, 1])
        self._plot_completion_pie(ax2)
        
        # 3. 效率对比
        ax3 = fig.add_subplot(gs[0, 2])
        self._plot_efficiency_comparison(ax3)
        
        # 4. 异常分析
        ax4 = fig.add_subplot(gs[1, :])
        self._plot_exception_analysis(ax4)
        
        # 5. 资源利用率
        ax5 = fig.add_subplot(gs[2, 0])
        self._plot_resource_utilization(ax5)
        
        # 6. 时间分布
        ax6 = fig.add_subplot(gs[2, 1:])
        self._plot_time_distribution(ax6)
        
        plt.suptitle('外卖流水线仿真仪表板', fontsize=16, fontweight='bold')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def _plot_summary_stats(self, ax):
        """绘制总体统计"""
        ax.set_title('总体统计', fontweight='bold')
        
        stats = [
            ('总订单', self.summary['total_orders']),
            ('完成订单', self.summary['completed_orders']),
            ('失败订单', self.summary['failed_orders']),
            ('总异常', self.summary['total_exceptions'])
        ]
        
        values = [stat[1] for stat in stats]
        labels = [stat[0] for stat in stats]
        colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12']
        
        bars = ax.bar(labels, values, color=colors, alpha=0.7)
        
        # 添加数值标签
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{value}', ha='center', va='bottom')
        
        ax.set_ylabel('数量')
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_completion_pie(self, ax):
        """绘制完成率饼图"""
        ax.set_title('订单完成情况', fontweight='bold')
        
        completed = self.summary['completed_orders']
        failed = self.summary['failed_orders']
        
        if completed + failed == 0:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center')
            return
        
        sizes = [completed, failed]
        labels = ['已完成', '失败']
        colors = ['#2ecc71', '#e74c3c']
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        
        # 添加完成率文本
        completion_rate = completed / (completed + failed) * 100
        ax.text(0, -1.3, f'完成率: {completion_rate:.1f}%', ha='center', fontweight='bold')
    
    def _plot_efficiency_comparison(self, ax):
        """绘制效率对比"""
        ax.set_title('效率对比', fontweight='bold')
        
        if self.summary['avg_ideal_time'] == 0:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center')
            return
        
        ideal_time = self.summary['avg_ideal_time']
        actual_time = self.summary['avg_actual_time']
        efficiency = self.summary['efficiency'] * 100
        
        categories = ['理想时间', '实际时间']
        values = [ideal_time, actual_time]
        colors = ['#2ecc71', '#3498db']
        
        bars = ax.bar(categories, values, color=colors, alpha=0.7)
        
        # 添加数值标签
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{value:.1f}min', ha='center', va='bottom')
        
        ax.set_ylabel('时间 (分钟)')
        ax.text(0.5, -0.15, f'效率: {efficiency:.1f}%', ha='center', transform=ax.transAxes, fontweight='bold')
    
    def _plot_exception_analysis(self, ax):
        """绘制异常分析"""
        ax.set_title('异常事件分析', fontweight='bold')
        
        # 统计异常类型
        exception_data = [d for d in self.pipeline_data if '异常' in d['details']]
        
        if not exception_data:
            ax.text(0.5, 0.5, '无异常事件', ha='center', va='center')
            return
        
        # 提取异常类型
        exception_types = {}
        for exc in exception_data:
            detail = exc['details']
            if '异常:' in detail:
                exc_type = detail.split('异常:')[1].split(',')[0]
                exception_types[exc_type] = exception_types.get(exc_type, 0) + 1
        
        if exception_types:
            types = list(exception_types.keys())
            counts = list(exception_types.values())
            
            bars = ax.bar(types, counts, color='#e74c3c', alpha=0.7)
            
            # 添加数值标签
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{count}', ha='center', va='bottom')
            
            ax.set_ylabel('异常次数')
            ax.tick_params(axis='x', rotation=45)
        else:
            ax.text(0.5, 0.5, '异常数据解析失败', ha='center', va='center')
    
    def _plot_resource_utilization(self, ax):
        """绘制资源利用率"""
        ax.set_title('资源利用率', fontweight='bold')
        
        merchants = self.results['resources']['merchants']
        riders = self.results['resources']['riders']
        
        # 计算利用率（基于处理的订单数）
        merchant_util = [m.total_processed for m in merchants]
        rider_util = [r.total_processed for r in riders]
        
        x = np.arange(max(len(merchants), len(riders)))
        width = 0.35
        
        if merchant_util:
            ax.bar(x[:len(merchants)] - width/2, merchant_util, width, label='商家', color='#f39c12', alpha=0.7)
        if rider_util:
            ax.bar(x[:len(riders)] + width/2, rider_util, width, label='骑手', color='#9b59b6', alpha=0.7)
        
        ax.set_xlabel('资源编号')
        ax.set_ylabel('处理订单数')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_time_distribution(self, ax):
        """绘制时间分布"""
        ax.set_title('订单处理时间分布', fontweight='bold')
        
        completed_orders = [o for o in self.orders if o.status.value == '已送达']
        
        if not completed_orders:
            ax.text(0.5, 0.5, '暂无完成订单', ha='center', va='center')
            return
        
        actual_times = [o.get_total_time() for o in completed_orders]
        ideal_times = [o.get_ideal_time() for o in completed_orders]
        
        # 绘制直方图
        ax.hist(ideal_times, bins=10, alpha=0.7, label='理想时间', color='#2ecc71', density=True)
        ax.hist(actual_times, bins=10, alpha=0.7, label='实际时间', color='#3498db', density=True)
        
        # 添加均值线
        ax.axvline(np.mean(ideal_times), color='#2ecc71', linestyle='--', linewidth=2, label=f'理想均值: {np.mean(ideal_times):.1f}')
        ax.axvline(np.mean(actual_times), color='#3498db', linestyle='--', linewidth=2, label=f'实际均值: {np.mean(actual_times):.1f}')
        
        ax.set_xlabel('时间 (分钟)')
        ax.set_ylabel('密度')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def generate_report(self, save_path: str = None) -> str:
        """生成文本报告"""
        report = []
        report.append("=" * 60)
        report.append("外卖流水线仿真分析报告")
        report.append("=" * 60)
        report.append("")
        
        # 基本统计
        report.append("【基本统计】")
        report.append(f"总订单数: {self.summary['total_orders']}")
        report.append(f"完成订单数: {self.summary['completed_orders']}")
        report.append(f"失败订单数: {self.summary['failed_orders']}")
        report.append(f"完成率: {self.summary['completion_rate']:.2%}")
        report.append("")
        
        # 时间分析
        report.append("【时间分析】")
        report.append(f"平均理想时间: {self.summary['avg_ideal_time']:.1f} 分钟")
        report.append(f"平均实际时间: {self.summary['avg_actual_time']:.1f} 分钟")
        report.append(f"系统效率: {self.summary['efficiency']:.2%}")
        report.append(f"总延迟时间: {self.summary['total_delay']:.1f} 分钟")
        report.append("")
        
        # 异常分析
        report.append("【异常分析】")
        report.append(f"总异常次数: {self.summary['total_exceptions']}")
        if self.summary['total_orders'] > 0:
            exception_rate = self.summary['total_exceptions'] / self.summary['total_orders']
            report.append(f"异常率: {exception_rate:.2%}")
        report.append("")
        
        # 改进建议
        report.append("【改进建议】")
        if self.summary['completion_rate'] < 0.9:
            report.append("- 完成率偏低，建议增加资源或优化异常处理")
        if self.summary['efficiency'] < 0.8:
            report.append("- 效率偏低，建议优化流程或减少异常")
        if self.summary['total_exceptions'] > self.summary['total_orders'] * 0.2:
            report.append("- 异常率过高，建议加强系统稳定性")
        
        report_text = "\n".join(report)
        
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text

# 测试代码
if __name__ == "__main__":
    # 这里需要从simulation.py导入并运行仿真
    print("请先运行 simulation.py 获取结果，然后使用 PipelineVisualizer 进行可视化")

