import os
import sys
import argparse

# 添加当前目录到Python路径，以便导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ClashUpdater import ClashUpdater

def main():
    """
    主程序入口
    """
    parser = argparse.ArgumentParser(description="Free VPN Clash Updater - 更新Clash配置的工具")
    parser.add_argument("-c", "--config", help="配置文件路径", default=None)
    parser.add_argument("-o", "--output", help="输出文件路径", default=None)
    parser.add_argument("-v", "--version", action="version", version="Free VPN Clash Updater 1.0")
    
    args = parser.parse_args()
    
    try:
        # 创建更新器实例
        updater = ClashUpdater()
        
        # 更新配置
        updater.update_clash_config(args.config, args.output)
        
        print("\n操作完成！")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n操作已取消！")
        sys.exit(1)
    except Exception as e:
        print(f"\n操作失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()