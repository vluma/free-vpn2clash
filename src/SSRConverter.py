import base64
import re
import yaml
import os
import sys
import json

# 添加当前目录到Python路径，以便导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class ConfigManager:
    def load_configuration(self, config_file=None):
        """
        加载配置文件
        
        Args:
            config_file (str, optional): 配置文件路径. 默认从config/config.yaml加载
            
        Returns:
            dict: 配置字典
        """
        import yaml
        
        # 默认配置文件路径
        if not config_file:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(current_dir, "../config/config.yaml")
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 添加默认值（如果配置项不存在）
            config = self._add_defaults(config)
            
            return config
            
        except yaml.YAMLError as e:
            raise Exception(f"解析配置文件失败: {str(e)}")
        except Exception as e:
            raise Exception(f"加载配置文件失败: {str(e)}")
    
    def _add_defaults(self, config):
        """
        为配置添加默认值
        
        Args:
            config (dict): 配置字典
            
        Returns:
            dict: 更新后的配置字典
        """
        defaults = {
            "ssr_source": {
                "urls": ["https://github.com/Alvin9999/new-pac/wiki/ss%E5%85%8D%E8%B4%B9%E8%B4%A6%E5%8F%B7", "https://gitlab.com/zhifan999/fq/-/wikis/ss%E5%85%8D%E8%B4%B9%E8%B4%A6%E5%8F%B7", "https://github.com/junjun266/FreeProxyGo"],
                "request_timeout": 30,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
            "output": {
                "directory": "./output",
                "clash_config_file": "clash_config.yaml"
            },
            "clash": {
                "port": 7890,
                "socks_port": 7891,
                "allow_lan": True,
                "mode": "Rule",
                "log_level": "info",
                "dns": {
                    "enable": True,
                    "listen": "0.0.0.0:53",
                    "enhanced_mode": "fake-ip",
                    "nameserver": ["114.114.114.114", "8.8.8.8"]
                },
                "rules": [
                    "DOMAIN-SUFFIX,google.com,PROXY",
                    "DOMAIN-SUFFIX,facebook.com,PROXY",
                    "DOMAIN-SUFFIX,youtube.com,PROXY",
                    "GEOIP,CN,DIRECT",
                    "MATCH,PROXY"
                ]
            },
            "clash_verge": {
                "config_directory": "",
                "auto_restart": False,
                "restart_timeout": 5
            }
        }
        
        # 递归合并配置
        return self._merge_dicts(defaults, config)
    
    def _merge_dicts(self, defaults, config):
        """
        递归合并两个字典
        
        Args:
            defaults (dict): 默认配置字典
            config (dict): 用户配置字典
            
        Returns:
            dict: 合并后的字典
        """
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
            elif isinstance(value, dict) and isinstance(config[key], dict):
                config[key] = self._merge_dicts(value, config[key])
        
        return config

class SSRConverter:
    def __init__(self):
        self.config_manager = ConfigManager()
    
    def convert_ssr_nodes_to_clash_config(self, ssr_nodes, config_file=None, output_file=None):
        """
        将SSR节点列表转换为Clash配置格式
        
        Args:
            ssr_nodes (list): SSR/VMess节点列表，每个节点是一个元组 (node_url, source_url)
            config_file (str, optional): 配置文件路径
            output_file (str, optional): 输出文件路径
            
        Returns:
            dict: Clash配置字典
        """
        if not ssr_nodes:
            raise ValueError("节点列表为空")
        
        # 加载配置
        config = self.config_manager.load_configuration(config_file)
        clash_config = config.get("clash", {})
        clash_config = {
            "port": clash_config.get("port", 7890),
            "socks-port": clash_config.get("socks_port", 7891),
            "allow-lan": clash_config.get("allow_lan", True),
            "mode": clash_config.get("mode", "Rule"),
            "log-level": clash_config.get("log_level", "info"),
            "external-controller": clash_config.get("external_controller", "127.0.0.1:9090"),
            "secret": clash_config.get("secret", ""),
            "dns": clash_config.get("dns", {
                "enable": True,
                "listen": "0.0.0.0:53",
                "enhanced-mode": "fake-ip",
                "nameserver": [
                    "114.114.114.114",
                    "8.8.8.8"
                ]
            }),
            "rule-providers": clash_config.get("rule-providers", {}),
            "rules": clash_config.get("rules", [
                "DOMAIN-SUFFIX,google.com,PROXY",
                "DOMAIN-SUFFIX,facebook.com,PROXY",
                "DOMAIN-SUFFIX,youtube.com,PROXY",
                "GEOIP,CN,DIRECT",
                "MATCH,PROXY"
            ]),
            "proxy-groups": clash_config.get("proxy-groups", []),
            "proxies": []
        }
        
        # 按来源URL分组存储节点
        nodes_by_source = {}
        
        # 转换每个节点，使用集合进行去重
        proxy_keys = set()
        for i, node_item in enumerate(ssr_nodes):
            try:
                # 检查节点格式（支持旧格式和新格式）
                if isinstance(node_item, tuple) and len(node_item) >= 2:
                    node_url, source_url = node_item
                else:
                    node_url = node_item
                    source_url = "未知来源"
                
                if node_url.startswith('ssr://'):
                    proxy = self._parse_ssr_url(node_url)
                elif node_url.startswith('vmess://'):
                    proxy = self._parse_vmess_url(node_url)
                elif node_url.startswith('ss://'):
                    proxy = self._parse_ss_url(node_url)
                elif node_url.startswith('vless://'):
                    proxy = self._parse_vless_url(node_url)
                else:
                    raise ValueError(f"不支持的节点类型: {node_url[:20]}...")
                
                # 生成唯一键并检查是否已存在
                proxy_key = self._generate_proxy_unique_key(proxy)
                if proxy_key not in proxy_keys:
                    proxy_keys.add(proxy_key)
                    clash_config["proxies"].append(proxy)
                    
                    # 将节点添加到对应的来源分组
                    if source_url not in nodes_by_source:
                        nodes_by_source[source_url] = []
                    nodes_by_source[source_url].append(proxy["name"])
                    
                    print(f"成功添加节点: {proxy['name']} (来源: {source_url})")
                else:
                    print(f"跳过重复节点: {proxy['name']}")
            except Exception as e:
                # 处理不同格式的节点
                node_url = node_item[0] if isinstance(node_item, tuple) else node_item
                print(f"转换节点失败 {node_url[:50]}...: {str(e)}")
        
        print(f"总共转换了 {len(clash_config['proxies'])} 个唯一节点")
        
        # 添加代理组（仅当有代理时）
        if clash_config["proxies"]:
            # 获取所有代理名称
            all_proxy_names = [proxy["name"] for proxy in clash_config["proxies"]]
            
            # 从配置中获取现有的代理组（如果有）
            proxy_groups = clash_config.get("proxy-groups", [])
            
            # 更新或添加"AUTO-SWITCH"组
            auto_switch_group_exists = False
            for group in proxy_groups:
                if group["name"] == "AUTO-SWITCH":
                    group["proxies"] = all_proxy_names
                    auto_switch_group_exists = True
                    break
            if not auto_switch_group_exists:
                proxy_groups.append({
                    "name": "AUTO-SWITCH",
                    "type": "url-test",
                    "url": "http://www.gstatic.com/generate_204",
                    "interval": 300,
                    "tolerance": 50,
                    "proxies": all_proxy_names
                })
            
            # 更新FREE-PROXY组，确保它包含AUTO-SWITCH、来源分组和所有节点作为选项
            proxy_group_exists = False
            for group in proxy_groups:
                if group["name"] == "FREE-PROXY":
                    # 清空现有代理列表，重新构建
                    group["proxies"] = []
                    
                    # 添加AUTO-SWITCH组
                    if "AUTO-SWITCH" not in group["proxies"]:
                        group["proxies"].append("AUTO-SWITCH")
                    
                    proxy_group_exists = True
                    break
            if not proxy_group_exists:
                # 创建FREE-PROXY组并添加到最上方
                free_proxy_group = {
                    "name": "FREE-PROXY",
                    "type": "select",
                    "proxies": ["AUTO-SWITCH"]
                }
                proxy_groups.insert(0, free_proxy_group)
            
            # 更新或添加按来源分组的代理组
            existing_group_names = {group["name"]: group for group in proxy_groups}
            for source_url, proxy_names in nodes_by_source.items():
                # 清理来源URL，使其适合作为组名
                group_name = self._clean_source_url_for_group_name(source_url)
                
                if group_name in existing_group_names:
                    # 更新已存在的代理组的proxies列表
                    existing_group_names[group_name]["proxies"] = proxy_names
                else:
                    # 添加新的代理组
                    proxy_groups.append({
                        "name": group_name,
                        "type": "select",
                        "proxies": proxy_names
                    })
            
            # 更新FREE-PROXY组，添加来源分组和所有节点
            for group in proxy_groups:
                if group["name"] == "FREE-PROXY":
                    # 添加来源分组
                    for source_url in nodes_by_source.keys():
                        group_name = self._clean_source_url_for_group_name(source_url)
                        if group_name not in group["proxies"]:
                            group["proxies"].append(group_name)
                    
                    # 添加所有节点
                    for proxy_name in all_proxy_names:
                        if proxy_name not in group["proxies"]:
                            group["proxies"].append(proxy_name)
                    break
            
            clash_config["proxy-groups"] = proxy_groups
        else:
            # 如果没有代理，仍然保留配置文件中的代理组
            clash_config["proxy-groups"] = clash_config.get("proxy-groups", [])
        
        # 从配置获取输出目录和文件名
        output_config = config.get("output", {})
        output_dir = output_config.get("directory", "./output")
        default_output_file = output_config.get("clash_config_file", "clash_config.yaml")
        
        # 如果没有提供输出文件路径，使用配置中的默认路径
        if not output_file:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, default_output_file)
        
        # 保存配置前的检查
        if len(clash_config["proxies"]) > 0:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 检查文件是否存在
            file_exists = os.path.exists(output_file)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(clash_config, f, allow_unicode=True, default_flow_style=False)
            
            if file_exists:
                print(f"已更新文件: {output_file}，添加了 {len(clash_config['proxies'])} 个节点")
            else:
                print(f"已创建文件: {output_file}，添加了 {len(clash_config['proxies'])} 个节点")
        else:
            print(f"节点数组为空，未更新文件: {output_file}")
        
        return clash_config
    
    def _parse_ssr_url(self, ssr_url):
        """
        解析SSR URL并转换为Clash代理配置
        
        Args:
            ssr_url (str): SSR URL
            
        Returns:
            dict: Clash代理配置
        """
        if not ssr_url.startswith('ssr://'):
            raise ValueError("不是有效的SSR URL")
        
        # 去掉前缀并解码
        encoded_part = ssr_url[6:]
        
        # 处理URL安全的base64编码
        encoded_part = encoded_part.replace('-', '+').replace('_', '/')
        padding = '=' * ((4 - len(encoded_part) % 4) % 4)
        encoded_part += padding
        
        decoded = base64.b64decode(encoded_part).decode('utf-8')
        
        # 解析主参数部分和查询参数部分
        if '?' in decoded:
            main_part, params_part = decoded.split('?')
        else:
            main_part = decoded
            params_part = ''
        
        # 解析主部分：server:port:protocol:method:obfs:password
        parts = main_part.split(':')
        if len(parts) != 6:
            raise ValueError(f"SSR URL格式错误，主部分应为6个部分，实际为{len(parts)}个部分")
        
        server, port, protocol, method, obfs, password_part = parts
        
        # 密码部分可能包含结尾的'/'，需要移除
        if password_part.endswith('/'):
            password_part = password_part[:-1]
        
        # 处理密码部分的URL安全base64编码
        password_part = password_part.replace('-', '+').replace('_', '/')
        # 添加base64填充
        padding = '=' * ((4 - len(password_part) % 4) % 4)
        password_part += padding
        
        # 解析参数字符串
        params = {}
        if params_part:
            for param in params_part.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)  # 只在第一个=处分割，处理值中包含=的情况
                    # 处理URL安全的base64编码
                    value = value.replace('-', '+').replace('_', '/')
                    # 添加base64填充
                    padding = '=' * ((4 - len(value) % 4) % 4)
                    value += padding
                    try:
                        decoded_value = base64.b64decode(value).decode('utf-8')
                        params[key] = decoded_value
                    except Exception:
                        params[key] = value
        
        # 解码密码
        password = base64.b64decode(password_part).decode('utf-8')
        
        # 构造Clash代理配置 - 确保名称唯一
        base_name = params.get('remarks', 'SSR')
        # 使用协议、加密方式、混淆类型和密码的前8位确保名称唯一
        proxy_name = f"{base_name}_{server}_{port}_{protocol[:3]}_{method[:3]}_{obfs[:3]}_{password[:8]}"
        
        proxy = {
            "name": proxy_name,
            "type": "ssr",
            "server": server,
            "port": int(port),
            "protocol": protocol,
            "cipher": method,
            "obfs": obfs,
            "password": password,
            "udp": True
        }
        
        # 只添加非空参数
        protocol_param = params.get('protoparam')
        if protocol_param and protocol_param.strip():
            proxy["protocol-param"] = protocol_param
        
        obfs_param = params.get('obfsparam')
        if obfs_param and obfs_param.strip():
            proxy["obfs-param"] = obfs_param
        
        return proxy
    
    def _parse_vmess_url(self, vmess_url):
        """
        解析VMess URL并转换为Clash代理配置
        
        Args:
            vmess_url (str): VMess URL
            
        Returns:
            dict: Clash代理配置
        """
        if not vmess_url.startswith('vmess://'):
            raise ValueError("不是有效的VMess URL")
        
        # 去掉前缀并解码
        encoded_part = vmess_url[8:]
        
        # 处理URL安全的base64编码
        encoded_part = encoded_part.replace('-', '+').replace('_', '/')
        padding = '=' * ((4 - len(encoded_part) % 4) % 4)
        encoded_part += padding
        
        decoded = base64.b64decode(encoded_part).decode('utf-8')
        
        # 解析JSON
        vmess_config = json.loads(decoded)
        
        # 构造Clash代理配置 - 确保名称唯一
        base_name = vmess_config.get("ps", "VMess")
        server = vmess_config.get("add")
        port = vmess_config.get("port")
        uuid = vmess_config.get("id", "")
        network = vmess_config.get("net", "tcp")
        
        # 生成ws-opts的唯一标识部分（如果有）
        ws_unique_part = ""
        if network == "ws":
            import hashlib
            # 创建一个基础字符串包含所有ws相关配置
            ws_config_str = ""
            if "path" in vmess_config and vmess_config["path"]:
                ws_config_str += vmess_config["path"]
            if "host" in vmess_config and vmess_config["host"]:
                ws_config_str += vmess_config["host"]
            # 如果有ws配置，生成哈希；如果没有ws配置，也生成一个独特的哈希值
            ws_hash = hashlib.md5(ws_config_str.encode()).hexdigest()[:6]
            ws_unique_part = f"_{ws_hash}"
        
        # 使用UUID的前8位、网络类型和ws-opts标识确保名称唯一
        proxy_name = f"{base_name}_{server}_{port}_{uuid[:8]}_{network}{ws_unique_part}"
        
        proxy = {
            "name": proxy_name,
            "type": "vmess",
            "server": vmess_config.get("add"),
            "port": int(vmess_config.get("port")),
            "uuid": vmess_config.get("id"),
            "alterId": int(vmess_config.get("aid", 0)),
            "cipher": vmess_config.get("scy", "auto"),
            "tls": vmess_config.get("tls", "").lower() == "true",
            "skip-cert-verify": True,
            "network": vmess_config.get("net", "tcp"),
            "udp": True
        }
        
        # 添加额外参数
        if "host" in vmess_config and vmess_config["host"]:
            proxy["ws-opts"] = {"headers": {"Host": vmess_config["host"]}}
        
        if "path" in vmess_config and vmess_config["path"]:
            if "ws-opts" not in proxy:
                proxy["ws-opts"] = {}
            proxy["ws-opts"]["path"] = vmess_config["path"]
        
        if "sni" in vmess_config and vmess_config["sni"]:
            proxy["servername"] = vmess_config["sni"]
        
        return proxy
    
    def _parse_ss_url(self, ss_url):
        """
        解析SS URL并转换为Clash代理配置
        
        Args:
            ss_url (str): SS URL
            
        Returns:
            dict: Clash代理配置
        """
        if not ss_url.startswith('ss://'):
            raise ValueError("不是有效的SS URL")
        
        # 去掉前缀
        encoded_part = ss_url[5:]
        
        # 解析@符号分隔的两部分：base64(加密方式:密码) 和 服务器:端口
        if '@' not in encoded_part:
            raise ValueError("SS URL格式错误，缺少@符号")
        
        auth_part, server_part = encoded_part.split('@', 1)
        
        # 解析服务器和端口
        if ':' not in server_part:
            raise ValueError("SS URL格式错误，服务器部分缺少端口")
        
        # 处理可能包含路径或参数的服务器部分
        server_port_part = server_part.split('?')[0]
        
        # 处理可能包含注释的端口号（如:990#注释）
        if '#' in server_port_part:
            server_port_part = server_port_part.split('#')[0]
        
        server, port_str = server_port_part.rsplit(':', 1)
        port = int(port_str)
        
        # 解析加密方式和密码
        try:
            # 处理URL安全的base64编码
            auth_part = auth_part.replace('-', '+').replace('_', '/')
            padding = '=' * ((4 - len(auth_part) % 4) % 4)
            auth_part += padding
            
            decoded_auth = base64.b64decode(auth_part).decode('utf-8')
            
            if ':' not in decoded_auth:
                raise ValueError("SS URL格式错误，认证部分缺少加密方式和密码的分隔符")
            
            method, password = decoded_auth.split(':', 1)
        except Exception as e:
            raise ValueError(f"解析SS URL认证部分失败: {str(e)}")
        
        # 构造Clash代理配置 - 确保名称唯一
        # 使用加密方式和密码的前8位确保名称唯一
        proxy_name = f"SS_{server}_{port}_{method[:5]}_{password[:8]}"
        proxy = {
            "name": proxy_name,
            "type": "ss",
            "server": server,
            "port": port,
            "cipher": method,
            "password": password,
            "udp": True
        }
        
        return proxy
    
    def _generate_proxy_unique_key(self, proxy):
        """
        生成代理配置的唯一键，用于去重
        
        Args:
            proxy (dict): Clash代理配置
            
        Returns:
            str: 唯一键
        """
        # 基础属性
        base_key = f"{proxy['type']}_{proxy['server']}_{proxy['port']}"
        
        # 根据不同类型添加特定属性
        if proxy['type'] == 'ssr':
            return f"{base_key}_{proxy.get('protocol', '')}_{proxy.get('cipher', '')}_{proxy.get('obfs', '')}_{proxy.get('password', '')}"
        elif proxy['type'] == 'vmess':
            # 对vmess类型，添加更多属性来区分不同节点
            vmess_key = f"{base_key}_{proxy.get('uuid', '')}_{proxy.get('alterId', '')}_{proxy.get('cipher', '')}"
            # 添加network和ws-opts信息
            network = proxy.get('network', '')
            vmess_key += f"_{network}"
            if network == 'ws' and 'ws-opts' in proxy:
                ws_opts = proxy['ws-opts']
                if 'path' in ws_opts:
                    vmess_key += f"_{ws_opts['path']}"
                if 'headers' in ws_opts and 'Host' in ws_opts['headers']:
                    vmess_key += f"_{ws_opts['headers']['Host']}"
            return vmess_key
        elif proxy['type'] == 'ss':
            return f"{base_key}_{proxy.get('cipher', '')}_{proxy.get('password', '')}"
        elif proxy['type'] == 'vless':
            # 对vless类型，添加更多属性来区分不同节点
            vless_key = f"{base_key}_{proxy.get('uuid', '')}_{proxy.get('network', '')}"
            # 添加tls和servername信息
            if proxy.get('tls'):
                vless_key += f"_tls"
            if 'servername' in proxy:
                vless_key += f"_{proxy['servername']}"
            # 添加网络特定配置
            network = proxy.get('network', '')
            if network == 'ws' and 'ws-opts' in proxy:
                ws_opts = proxy['ws-opts']
                if 'path' in ws_opts:
                    vless_key += f"_{ws_opts['path']}"
                if 'headers' in ws_opts and 'Host' in ws_opts['headers']:
                    vless_key += f"_{ws_opts['headers']['Host']}"
            elif network == 'http' and 'http-opts' in proxy:
                http_opts = proxy['http-opts']
                if 'path' in http_opts:
                    vless_key += f"_{http_opts['path'][0]}" if http_opts['path'] else ""
                if 'method' in http_opts:
                    vless_key += f"_{http_opts['method']}"
            return vless_key
        else:
            return base_key
    
    def _clean_source_url_for_group_name(self, source_url):
        """
        清理来源URL，使其适合作为Clash配置中的分组名称
        
        Args:
            source_url (str): 来源URL
            
        Returns:
            str: 清理后的分组名称
        """
        import re
        
        # 特殊处理GitHub链接
        github_match = re.match(r'^https?://github\.com/([^/]+)/([^/]+)', source_url)
        if github_match:
            username = github_match.group(1)
            repo_name = github_match.group(2)
            # 移除可能的wiki路径
            repo_name = re.sub(r'/wiki.*$', '', repo_name)
            return f"Github - {username}/{repo_name}"
        
        # 移除协议部分 (http://, https://)
        group_name = re.sub(r'^https?://', '', source_url)
        
        # 移除路径部分
        group_name = re.sub(r'/.*$', '', group_name)
        
        # 移除端口号 (如果有)
        group_name = re.sub(r':\d+$', '', group_name)
        
        # 移除特殊字符，保留中文、英文、数字和部分标点
        group_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9.-_]', '', group_name)
        
        # 限制长度
        max_length = 30
        if len(group_name) > max_length:
            group_name = group_name[:max_length]
        
        # 如果处理后为空，使用默认名称
        if not group_name:
            group_name = "未知来源"
        
        return group_name
    
    def _parse_vless_url(self, vless_url):
        """
        解析VLESS URL并转换为Clash代理配置
        
        Args:
            vless_url (str): VLESS URL
            
        Returns:
            dict: Clash代理配置
        """
        if not vless_url.startswith('vless://'):
            raise ValueError("不是有效的VLESS URL")
        
        # 去掉前缀
        url_part = vless_url[8:]
        
        if '@' not in url_part:
            raise ValueError("VLESS URL格式错误，缺少@符号")
        
        uuid_part, server_part = url_part.split('@', 1)
        
        # 解析服务器和端口
        if ':' not in server_part:
            raise ValueError("VLESS URL格式错误，服务器部分缺少端口")
        
        # 处理可能包含路径或参数的服务器部分
        server_port_path, params_part = server_part.split('?', 1) if '?' in server_part else (server_part, '')
        
        if '/' in server_port_path:
            server_port_part, path_part = server_port_path.split('/', 1)
            path_part = '/' + path_part
        else:
            server_port_part = server_port_path
            path_part = ''
        
        server, port_str = server_port_part.rsplit(':', 1)
        port = int(port_str)
        
        # 解析参数字符串
        params = {}
        if params_part:
            for param in params_part.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
        
        # 处理网络类型
        network_type = params.get('type', params.get('net', 'tcp'))
        
        # 构造Clash代理配置 - 确保名称唯一
        base_name = params.get('remarks', 'VLESS')
        # 使用UUID的前8位和网络类型确保名称唯一
        proxy_name = f"{base_name}_{server}_{port}_{uuid_part[:8]}_{network_type}"
        
        # 处理安全协议
        security = params.get('security', '').lower()
        tls_enabled = security in ['tls', 'reality', 'xtls'] or params.get('tls', '').lower() == 'true'
        
        proxy = {
            "name": proxy_name,
            "type": "vless",
            "server": server,
            "port": port,
            "uuid": uuid_part,
            "network": network_type,
            "tls": tls_enabled,
            "udp": params.get('udp', '').lower() == 'true',
            "skip-cert-verify": True
        }
        
        # 处理TLS相关配置
        if tls_enabled:
            if 'sni' in params:
                proxy["servername"] = params['sni']
            if 'alpn' in params:
                proxy["alpn"] = params['alpn'].split(',')
            
            # 处理reality配置
            if security == 'reality':
                proxy["reality-opts"] = {}
                if 'pbk' in params:
                    proxy["reality-opts"]["public-key"] = params['pbk']
                if 'sid' in params:
                    proxy["reality-opts"]["short-id"] = params['sid']
                if 'fp' in params:
                    proxy["client-fingerprint"] = params['fp']
        
        # 处理网络类型特定的配置
        if network_type == 'ws':
            proxy["ws-opts"] = {}
            if path_part:
                proxy["ws-opts"]["path"] = path_part
            if 'host' in params:
                proxy["ws-opts"]["headers"] = {"Host": params['host']}
        elif network_type == 'grpc':
            proxy["grpc-opts"] = {"grpc-service-name": params.get('serviceName', '')}
        elif network_type == 'h2':
            proxy["h2-opts"] = {}
            if path_part:
                proxy["h2-opts"]["path"] = path_part
            if 'host' in params:
                proxy["h2-opts"]["host"] = [params['host']]
        elif network_type == 'xhttp':
            # xhttp是特殊的HTTP传输，需要特殊处理
            proxy["network"] = 'http'  # Clash中可能使用http
            proxy["http-opts"] = {
                "method": "GET",
                "path": [path_part] if path_part else ["/"]
            }
            if 'host' in params:
                proxy["http-opts"]["headers"] = {"Host": [params['host']]}
        
        return proxy
    
    def save_clash_config_to_file(self, clash_config, file_path):
        """
        将Clash配置保存到文件
        
        Args:
            clash_config (dict): Clash配置字典
            file_path (str): 输出文件路径
        """
        # 保存配置前的检查
        if len(clash_config.get("proxies", [])) > 0:
            # 确保输出目录存在
            dir_name = os.path.dirname(file_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            
            # 检查文件是否存在
            file_exists = os.path.exists(file_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(clash_config, f, allow_unicode=True, default_flow_style=False)
            
            if file_exists:
                print(f"已更新文件: {file_path}，添加了 {len(clash_config['proxies'])} 个节点")
            else:
                print(f"已创建文件: {file_path}，添加了 {len(clash_config['proxies'])} 个节点")
        else:
            print(f"节点数组为空，未更新文件: {file_path}")
