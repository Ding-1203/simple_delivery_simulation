import os
import argparse
import time
from simulation import DeliveryPipeline
from visualization import PipelineVisualizer
from simulation import SIMULATION_TIME

def create_new_output_dir(base_output: str) -> str:
    """创建新的输出目录，每次运行生成一个新的目录"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")  # 使用当前时间戳来命名目录
    output_dir = f"{base_output}_{timestamp}"

    # 如果目录不存在，则创建
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    return output_dir

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='外卖流水线仿真系统')
    parser.add_argument('--duration', type=int, default=SIMULATION_TIME, help='仿真时长（分钟）')
    parser.add_argument('--no-viz', action='store_true', help='不显示可视化')
    parser.add_argument('--output', type=str, default='results', help='输出目录前缀')

    args = parser.parse_args()

    print("启动外卖流水线仿真系统")
    print("=" * 50)

    # 创建新的输出目录
    output_dir = create_new_output_dir(args.output)
    print(f"结果将输出到目录: {output_dir}")

    # 运行仿真
    print("运行仿真...")
    sim = DeliveryPipeline()
    results = sim.run(args.duration)

    # 显示基本结果
    print("\n仿真结果摘要:")
    summary = results['summary']
    print(f"  总订单: {summary['total_orders']}")
    print(f"  完成订单: {summary['completed_orders']}")
    print(f"  失败订单: {summary['failed_orders']}")
    print(f"  完成率: {summary['completion_rate']:.1%}")
    print(f"  平均实际时间: {summary['avg_actual_time']:.1f}分钟")
    print(f"  平均理想时间: {summary['avg_ideal_time']:.1f}分钟")
    print(f"  系统效率: {summary['efficiency']:.1%}")
    print(f"  总异常数: {summary['total_exceptions']}")
    print(f"  总延迟: {summary['total_delay']:.1f}分钟")

    # 可视化分析
    if not args.no_viz:
        print("\n生成可视化分析...")
        try:
            visualizer = PipelineVisualizer(results)

            # 生成流水线流程图
            print("  - 流水线流程图")
            visualizer.create_pipeline_flow_chart(os.path.join(output_dir, f"pipeline_flow.png"))

            # 生成仪表板
            print("  - 综合仪表板")
            visualizer.create_pipeline_dashboard(os.path.join(output_dir, f"dashboard.png"))

            # 生成报告
            print("  - 分析报告")
            report = visualizer.generate_report(os.path.join(output_dir, f"report.txt"))

            print("\n详细分析报告:")
            print(report)

        except Exception as e:
            print(f" 可视化生成失败: {e}")
            print(" 建议使用 --no-viz 参数只运行仿真")

    # 显示订单详情
    print("\n订单处理详情 (前20个):")
    print(f"{'订单ID':<7} {'状态':<7} {'实际用时':<8} {'理想用时':<8} {'延迟':<8} {'重试':<6} {'异常数'}")
    print("-" * 80)
    for order in results['orders'][:20]:
        total_time = order.get_total_time() or 0
        ideal_time = order.get_ideal_time()
        delay = order.total_delay
        status = order.status.value
        print(
            f"{order.id:<8} {status:<8} {total_time:<10.1f} {ideal_time:<10.1f} {delay:<10.1f} {order.retry_count:<6} {len(order.exceptions)}")

    print("\n仿真完成!")

    if not args.no_viz:
        print(f"结果文件:")
        print(f"  - {output_dir}/pipeline_flow.png (流水线流程图)")
        print(f"  - {output_dir}/dashboard.png (综合仪表板)")
        print(f"  - {output_dir}/report.txt (分析报告)")

if __name__ == "__main__":
    main()
