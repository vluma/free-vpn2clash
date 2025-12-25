import os
import sys
import yaml
import subprocess
import time

# 添加当前目录到Python路径，以便导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from SSRFetcher import SSRFetcher
from SSRConverter import SSRConverter

class ClashUpdater:
    def __init__(self):
        self.config_manager = self._create_config_manager()
        self.ssr_fetcher = SSRFetcher()
        self.ssr_converter = SSRConverter()
        
    def _create_config_manager(self):
        """
        创建配置管理器实例
        
        Returns:
            ConfigManager: 配置管理器实例
        """
        from SSRFetcher import ConfigManager
        return ConfigManager()
    
    def update_clash_config(self, config_file=None, output_file=None):
        """
        更新Clash配置文件
        
        Args:
            config_file (str, optional): 配置文件路径
            output_file (str, optional): 输出文件路径
            
        Returns:
            dict: 更新后的Clash配置
        """
        print("开始更新Clash配置...")
        
        # 加载配置
        config = self.config_manager.load_configuration(config_file)
        
        # 1. 获取节点
        print("\n1. 获取代理节点...")
        nodes_with_source = self.ssr_fetcher.get_nodes_from_web(config_file)
        
        if not nodes_with_source:
            raise Exception("未获取到任何代理节点")
        
        # 2. 转换节点为Clash配置
        print("\n2. 转换节点为Clash配置...")
        clash_config = self.ssr_converter.convert_ssr_nodes_to_clash_config(
            nodes_with_source, config_file, output_file
        )
        
        # 3. 检查Clash Verge配置
        clash_verge_config = config.get("clash_verge", {})
        config_directory = clash_verge_config.get("config_directory", "")
        auto_restart = clash_verge_config.get("auto_restart", False)
        
        if config_directory:
            print("\n3. 检查Clash Verge配置目录...")
            if not os.path.exists(config_directory):
                print(f"警告: Clash Verge配置目录不存在: {config_directory}")
            else:
                print(f"Clash Verge配置目录已存在: {config_directory}")
        
        # 4. 自动重启Clash Verge（如果配置了）
        if auto_restart:
            print("\n4. 自动重启Clash Verge...")
            self._restart_clash_verge(clash_verge_config)
        
        print("\nClash配置更新完成！")
        return clash_config
    
    def _restart_clash_verge(self, clash_verge_config):
        """
        重启Clash Verge
        
        Args:
            clash_verge_config (dict): Clash Verge配置
        """
        try:
            restart_timeout = clash_verge_config.get("restart_timeout", 5)
            
            # 关闭Clash Verge
            print("正在关闭Clash Verge...")
            subprocess.run(["taskkill", "/f", "/im", "Clash Verge.exe"], 
                          capture_output=True, text=True, check=False)
            
            # 等待一段时间
            time.sleep(restart_timeout)
            
            # 启动Clash Verge
            print("正在启动Clash Verge...")
            subprocess.run(["start", "Clash Verge"], shell=True, capture_output=True, text=True)
            
            print("Clash Verge重启成功！")
        except Exception as e:
            print(f"重启Clash Verge失败: {str(e)}")
    
    def update_clash_verge_config(self, config_file=None, output_file=None):
        """
        更新Clash Verge配置（兼容旧方法名）
        
        Args:
            config_file (str, optional): 配置文件路径
            output_file (str, optional): 输出文件路径
            
        Returns:
            dict: 更新后的Clash配置
        """
        return self.update_clash_config(config_file, output_file)

if __name__ == "__main__":
    updater = ClashUpdater()
    updater.update_clash_config()