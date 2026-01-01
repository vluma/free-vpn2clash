# free-vpn2clash

从多个源获取免费代理节点并生成Clash配置文件，支持订阅。

## 功能特性

- 从多个源URL获取免费代理节点（SSR、VMess、VLESS、SS协议）
- 自动生成Clash配置文件（output/clash_config.yaml）
- 支持代理节点去重和命名唯一化
- 配置文件驱动，支持自定义源URL和规则

## 项目结构

```
free-vpn2clash/
├── config/              # 配置文件目录
│   └── config.yaml      # 主配置文件
├── output/              # 输出目录
│   └── clash_config.yaml # 生成的Clash配置文件
├── src/                 # 源代码目录
│   ├── ClashUpdater.py  # Clash配置更新类
│   ├── SSRConverter.py  # 代理节点转换类
│   ├── SSRFetcher.py    # 代理节点获取类
│   └── main.py          # 主程序入口
├── requirements.txt     # 依赖库列表
└── .gitignore           # Git忽略文件
```

## 安装和使用

1. 安装依赖库：
```bash
pip install -r requirements.txt
```

2. 运行主程序：
```bash
python -m src.main
```

3. 生成的Clash配置文件将保存在`output/clash_config.yaml`

## 订阅地址

您可以直接使用以下订阅链接导入Clash配置：

```
https://raw.githubusercontent.com/vluma/free-vpn2clash/refs/heads/main/output/free-VPN.yaml
```

将此链接添加到Clash客户端中即可自动获取最新的免费代理节点配置。

## 推荐软件
PC 端推荐 *[**Clash Verge**](https://www.clashverge.dev/install.html)* ，支持 **Windows、Linux、macOS**

Android 端推荐 *[**ClashMetaForAndroid**](https://github.com/MetaCubeX/ClashMetaForAndroid/releases)* ，支持 **Android**

iOS 端推荐 **Shadowrocket** 从 **Apple Store** 下载（需付费），支持 **iOS**，需要美国账号。

鸿蒙端推荐 *[**ClashBox**](https://github.com/xiaobaigroup/ClashBox/releases)* ，支持 **HarmonyOS**



## 配置说明

配置文件位于`config/config.yaml`，主要包含以下部分：

- `source_urls`：代理节点源URL列表
- `clash_config`：Clash配置模板
- `rules`：Clash规则列表

您可以根据需要修改配置文件来自定义源URL和规则。
