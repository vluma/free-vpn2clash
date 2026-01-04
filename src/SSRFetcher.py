import re
import os
import sys
import requests
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
from playwright.sync_api import sync_playwright

# 添加当前目录到Python路径，以便导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bs4 import BeautifulSoup

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
                "urls": ["https://github.com/Alvin9999/new-pac/wiki/ss%E5%85%8D%E8%B4%B9%E8%B4%A6%E5%8F%B7", "https://github.com/junjun266/FreeProxyGo"],
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

class SSRFetcher:
    def __init__(self):
        self.config_manager = ConfigManager()
    
    def get_nodes_from_web(self, config_file=None, custom_urls=None):
        """
        从多个Web页面并发获取代理节点列表
        
        Args:
            config_file (str, optional): 配置文件路径
            custom_urls (list or str, optional): 自定义URL列表或单个URL，优先使用此URL
            
        Returns:
            list: 代理节点列表，每个节点是一个元组 (node_url, source_url)
        """
        # 加载配置
        config = self.config_manager.load_configuration(config_file)
        ssr_source = config.get("ssr_source", {})
        
        # 处理自定义URLs参数
        if custom_urls:
            if isinstance(custom_urls, str):
                urls = [custom_urls]
            else:
                urls = custom_urls
        else:
            urls = ssr_source.get("urls", [])
        
        user_agent = ssr_source.get("user_agent")
        timeout = ssr_source.get("request_timeout")

        if not urls:
            raise ValueError("配置中未设置ssr_source.urls")

        print(f"尝试使用URL列表: {urls}")
        
        all_nodes_with_source = []
        max_workers = 5  # 最大并发数
        
        # 使用线程池并发获取所有URL
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_url = {
                executor.submit(self._fetch_and_parse_nodes, url, user_agent, timeout): url
                for url in urls
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    nodes = future.result()
                    print(f"URL {url} 成功获取到 {len(nodes)} 个节点")
                    # 添加来源信息，每个节点作为元组 (node_url, source_url)
                    for node in nodes:
                        all_nodes_with_source.append((node, url))
                except Exception as e:
                    print(f"URL {url} 请求失败: {str(e)}")
        
        if not all_nodes_with_source:
            raise Exception("所有URL都未能获取到节点")
        
        # 去重，保留每个唯一节点及其第一个来源
        unique_nodes_with_source = []
        seen_nodes = set()
        for node, source_url in all_nodes_with_source:
            if node not in seen_nodes:
                seen_nodes.add(node)
                unique_nodes_with_source.append((node, source_url))
        
        print(f"总共获取到 {len(all_nodes_with_source)} 个节点，去重后剩余 {len(unique_nodes_with_source)} 个节点")
        
        return unique_nodes_with_source
    
    def _fetch_and_parse_nodes(self, url, user_agent=None, timeout=None):
        """
        从指定URL获取并解析节点
        
        Args:
            url (str): 要获取的URL
            user_agent (str): User-Agent字符串
            timeout (int): 请求超时时间（秒）
            
        Returns:
            list: 提取的节点列表
        """
        import json
        import html
        import time
        
        max_retries = 3  # 最大重试次数
        retry_delay = 5  # 初始重试延迟（秒）
        
        for retry in range(max_retries):
            try:
                print(f"尝试获取URL内容，第{retry+1}/{max_retries}次尝试")
                
                # 获取页面HTML
                raw_html = self._get_html_from_http(url, user_agent, timeout)
                
                # 检查是否获取到了有效的HTML
                if not raw_html or raw_html.strip() == "":
                    raise ValueError("获取到的HTML内容为空")
                
                ssr_nodes = []
                proxy_protocols = ['ssr://', 'vmess://', 'vless://', 'ss://', 'hysteria2://', 'trojan://']
                
                # 先尝试直接检测并处理base64编码的内容
                try:
                    # 检查是否为base64编码：只包含base64字符，且长度是4的倍数
                    # 移除可能的URL安全字符和空白字符，检查原始HTML内容
                    base64_candidate = raw_html.strip()
                    # 移除所有空白字符（包括换行符）
                    base64_candidate = re.sub(r'\s+', '', base64_candidate)
                    # 替换URL安全的base64字符
                    base64_candidate = base64_candidate.replace('-', '+').replace('_', '/')
                    # 检查是否只包含base64字符
                    if re.match(r'^[A-Za-z0-9+/]+={0,2}$', base64_candidate) and len(base64_candidate) % 4 == 0:
                        print("检测到可能的base64编码内容，尝试解码...")
                        # 添加必要的填充
                        padding = '=' * ((4 - len(base64_candidate) % 4) % 4)
                        base64_candidate += padding
                        # 解码base64
                        decoded_content = base64.b64decode(base64_candidate).decode('utf-8')
                        print(f"base64解码成功，内容长度: {len(decoded_content)} 字符")
                        print(f"解码后的内容前100字符: {decoded_content[:100]}...")
                        # 从解码后的内容中提取VPN链接
                        self._extract_ssr_nodes_from_text(decoded_content, ssr_nodes)
                        
                        # 如果成功提取到节点，直接返回
                        if ssr_nodes:
                            unique_nodes = list(set(ssr_nodes))
                            print(f"从base64内容中提取到 {len(unique_nodes)} 个节点")
                            return unique_nodes
                except Exception as e:
                    print(f"base64解码失败，继续使用原始HTML内容: {str(e)}")
                    # 解码失败，继续使用原始HTML内容
                    pass
                
                # 原始内容不是base64编码，继续使用BeautifulSoup解析
                html_content = raw_html
                soup = BeautifulSoup(html_content, 'lxml')
                raw_text = soup.get_text()
                clean_text = " ".join(raw_text.split())
                
                print(f"开始解析URL {url} 的HTML内容")
                # 检查解析后的内容是否包含代理节点
                if any(proxy_type in html_content for proxy_type in proxy_protocols):
                    print("HTML内容中检测到代理节点")
                else:
                    print(f"URL {html_content[:100]}... 的HTML内容中未检测到直接的代理节点")
                    print(f"HTML内容长度: {len(soup.get_text())} 字符")
                    print(f"HTML内容: {clean_text[:100]}... 字符")

                    print("HTML内容中未直接检测到代理节点")
                    html_content = self._get_html_from_browser(url, user_agent, timeout)
                    # 重新创建soup对象
                    soup = BeautifulSoup(html_content, 'lxml')
                
                # 特殊处理GitLab Wiki页面的data-page-info属性
                if 'gitlab.com' in url:
                    print("检测到GitLab URL，尝试解析data-page-info属性...")
                    div_with_data = soup.find('div', {'data-page-info': True})
                    if div_with_data:
                        page_info = div_with_data['data-page-info']
                        
                        # 尝试解析JSON获取wiki内容
                        try:
                            # 解码HTML实体
                            decoded_page_info = html.unescape(page_info)
                            json_data = json.loads(decoded_page_info)
                            
                            if 'content' in json_data:
                                wiki_content = json_data['content']
                                print(f"从GitLab data-page-info提取到Wiki内容，长度: {len(wiki_content)} 字符")
                                self._extract_ssr_nodes_from_text(wiki_content, ssr_nodes)
                        except Exception as e:
                            print(f"解析GitLab data-page-info失败: {str(e)}")
                
                # 1. 查找所有代码块
                code_blocks = soup.find_all(['pre', 'code'])
                print(f"找到 {len(code_blocks)} 个代码块")
                for block in code_blocks:
                    code_text = block.get_text()
                    self._extract_ssr_nodes_from_text(code_text, ssr_nodes)
                
                # 2. 查找所有链接
                links = soup.find_all('a')
                for link in links:
                    href = link.get('href')
                    if href and any(href.startswith(proxy_type) for proxy_type in proxy_protocols):
                        ssr_nodes.append(href)
                
                # 3. 查找所有段落文本
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    text = p.get_text()
                    self._extract_ssr_nodes_from_text(text, ssr_nodes)
                
                # 4. 查找所有列表项
                list_items = soup.find_all('li')
                for li in list_items:
                    text = li.get_text()
                    self._extract_ssr_nodes_from_text(text, ssr_nodes)
                
                # 5. 直接从整个页面文本中搜索
                self._extract_ssr_nodes_from_text(soup.get_text(), ssr_nodes)
                
                # 去重
                unique_nodes = list(set(ssr_nodes))
                
                if unique_nodes:
                    print(f"第{retry+1}次尝试成功，获取到 {len(unique_nodes)} 个节点")
                    return unique_nodes
                else:
                    print(f"第{retry+1}次尝试未获取到任何节点，准备重试...")
                    
            except Exception as e:
                print(f"第{retry+1}次尝试失败: {str(e)}")
                
                # 如果不是最后一次重试，等待后继续
                if retry < max_retries - 1:
                    wait_time = retry_delay * (2 ** retry)  # 指数退避
                    print(f"等待 {wait_time} 秒后进行第{retry+2}次尝试")
                    time.sleep(wait_time)
                else:
                    print(f"已达到最大重试次数 {max_retries}，放弃获取")
                    raise
        
        # 如果所有重试都失败，返回空列表
        return []
    
    def _get_html_from_http(self, url, user_agent=None, timeout=None):
        # 默认值
        default_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        default_timeout = 30
        
        # 发送HTTP请求
        headers = {
            'User-Agent': user_agent or default_user_agent
        }
        
        response = requests.get(url, headers=headers, timeout=timeout or default_timeout)
        response.raise_for_status()  # 检查请求是否成功
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"HTTP请求失败，状态码: {response.status_code}")

    def _get_html_from_browser(self, url, user_agent=None, timeout=None):
        # 默认值
        default_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        default_timeout = 30  # 减少默认超时时间
        
        html_content = None
        captured_requests = []
        captured_responses = []
        api_responses_with_proxies = []
        
        with sync_playwright() as p:
            browser = None
            context = None
            page = None
            
            try:
                # 启动浏览器（无头模式）
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=user_agent or default_user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = context.new_page()
                # 设置超时
                page.set_default_timeout((timeout or default_timeout) * 1000)
                
                # 捕获所有网络请求和响应
                def capture_request(request):
                    captured_requests.append({
                        'url': request.url,
                        'method': request.method,
                        'headers': dict(request.headers)
                    })
                    print(f"页面请求: {request.method} {request.url}")
                
                def capture_response(response):
                    request = response.request
                    captured_responses.append({
                        'url': request.url,
                        'method': request.method,
                        'status': response.status,
                        'headers': dict(response.headers)
                    })
                    print(f"页面响应: {response.status} {request.url}")
                    
                    # 检查响应是否可能包含代理节点数据
                    content_type = response.headers.get('content-type', '')
                    if any(subtype in content_type for subtype in ['application/json', 'text/plain', 'text/html']):
                        try:
                            # 在同步API中，使用response.text()方法获取内容
                            response_body = response.text()
                            
                            # 检查响应内容是否包含代理节点
                            if any(proxy_type in response_body for proxy_type in ['ssr://', 'vmess://', 'vless://', 'ss://', 'hysteria2://']):
                                print(f"响应 {request.url} 中检测到代理节点")
                                api_responses_with_proxies.append({
                                    'url': request.url,
                                    'body': response_body
                                })
                        except Exception as e:
                            print(f"读取响应 {request.url} 内容失败: {str(e)}")
                
                page.on('request', capture_request)
                page.on('response', capture_response)
                
                # 导航到URL并等待初始加载完成
                page.goto(url, wait_until='networkidle')
                
                # 等待URL稳定化（处理所有重定向）
                final_url = None
                stable_count = 0
                max_stable_checks = 2  # 2次检查 * 500ms = 1秒稳定时间
                for _ in range(5):  # 最多检查5次（2.5秒）
                    current_url = page.url
                    if current_url == final_url:
                        stable_count += 1
                        if stable_count >= max_stable_checks:
                            print(f"URL已稳定: {current_url}")
                            break
                    else:
                        final_url = current_url
                        stable_count = 0
                        print(f"URL已变更: {current_url}")
                    page.wait_for_timeout(500)
                
                # 等待网络空闲，确保所有资源加载完成
                page.wait_for_load_state('networkidle')
                print("网络已空闲")
                
                # 等待JavaScript有足够时间执行初始渲染
                page.wait_for_timeout(2000)
                
                # 单次滚动，确保动态内容加载
                print("执行滚动操作")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                
                # 等待网络空闲
                page.wait_for_load_state('networkidle')
                print("滚动完成后网络再次空闲")
                
                # 简化的内容稳定化检查
                previous_content = None
                content_stable_count = 0
                max_content_stable_checks = 2  # 2次检查 * 1秒 = 2秒内容稳定时间
                
                print("开始检查页面内容稳定化...")
                for _ in range(5):  # 最多检查5次（5秒）
                    current_content = page.inner_text('body')
                    if current_content == previous_content:
                        content_stable_count += 1
                        if content_stable_count >= max_content_stable_checks:
                            print("页面内容已稳定")
                            break
                    else:
                        previous_content = current_content
                        content_stable_count = 0
                        print(f"页面内容仍在变化，第{_+1}次检查")
                    page.wait_for_timeout(1000)  # 每1秒检查一次
                
                # 尝试直接执行JavaScript来获取页面中的代理节点
                proxy_nodes = []
                try:
                    proxy_nodes = page.evaluate("""
                        () => {
                            // 函数：在给定文档中查找所有代理节点
                            function findProxyNodes(doc) {
                                const text = doc.body.textContent;
                                const regex = new RegExp('(?:ssr|vmess|vless|ss)://[^\\s\\n\\r]*?(?=(?:ssr|vmess|vless|ss)://|$)', 'g');
                                return text.match(regex) || [];
                            }
                            
                            // 在主页面查找
                            return findProxyNodes(document);
                        }
                    """)
                    print(f"直接从JavaScript获取到的代理节点数量: {len(proxy_nodes)}")
                except Exception as e:
                    print(f"执行JavaScript获取代理节点失败: {str(e)}")
                
                # 检查是否从网络响应中获取到了代理节点
                if api_responses_with_proxies:
                    print(f"从API响应中获取到 {len(api_responses_with_proxies)} 个包含代理节点的响应")
                    
                    # 从API响应中提取所有代理节点
                    api_proxy_nodes = []
                    for response_data in api_responses_with_proxies:
                        body = response_data['body']
                        url = response_data['url']
                        
                        # 提取所有代理节点，使用与_extract_ssr_nodes_from_text相同的正则表达式
                        import re
                        matches = re.findall(r'(?:ssr|vmess|vless|ss|hysteria2)://[^\s\n\r]*?(?=(?:ssr|vmess|vless|ss)://|$)', body)
                        
                        if matches:
                            print(f"从响应 {url} 中提取到 {len(matches)} 个代理节点")
                            api_proxy_nodes.extend(matches)
                    
                    # 去重
                    api_proxy_nodes = list(set(api_proxy_nodes))
                    print(f"从API响应中提取到 {len(api_proxy_nodes)} 个唯一代理节点")
                    
                    # 创建包含API响应中代理节点的HTML
                    newline = '\n'
                    html_content = f"<html><body><pre>{newline.join(api_proxy_nodes)}</pre></body></html>"
                    print("已创建包含API响应中代理节点的HTML内容，方便后续处理")
                elif proxy_nodes:
                    # 如果直接从页面中获取到了代理节点，创建包含这些节点的HTML
                    newline = '\n'
                    html_content = f"<html><body><pre>{newline.join(proxy_nodes)}</pre></body></html>"
                    print("已创建包含页面代理节点的HTML内容")
                else:
                    # 继续尝试获取完整HTML
                    print("页面文本中仍然没有找到代理节点")
                    
                    # 获取完整的HTML内容
                    html_content = page.content()
                    print(f"获取到完整HTML内容，长度: {len(html_content)}")
            except Exception as e:
                print(f"使用Playwright获取URL {url} 失败: {str(e)}")
                raise
            finally:
                # 确保资源正确释放
                try:
                    if page:
                        page.close()
                        print("页面已关闭")
                except Exception as e:
                    print(f"关闭页面失败: {str(e)}")
                
                try:
                    if context:
                        context.close()
                        print("上下文已关闭")
                except Exception as e:
                    print(f"关闭上下文失败: {str(e)}")
                
                try:
                    if browser:
                        browser.close()
                        print("浏览器已关闭")
                except Exception as e:
                    print(f"关闭浏览器失败: {str(e)}")
    
        if not html_content:
            raise ValueError(f"无法获取URL {url} 的内容")
    
        return html_content
    
    def _extract_ssr_nodes_from_text(self, text, nodes_array):
        """
        从文本中提取节点
        
        Args:
            text (str): 要提取的文本
            nodes_array (list): 存储提取的节点的数组
        """
        # 正则表达式匹配ssr://、vmess://、vless://、ss://、hysteria2://和trojan://开头的链接
        # 对于有换行符分隔的节点，使用换行符作为分隔符
        # 对于没有换行符分隔的节点，使用下一个代理协议开头或字符串结束作为分隔符
        # 先按换行符分割文本，然后对每个部分使用正则表达式匹配
        lines = text.split('\n')
        for line in lines:
            # 移除空白字符
            line = line.strip()
            if not line:
                continue
            # 正则表达式匹配代理链接，直到遇到下一个代理协议开头或字符串结束
            ssr_vmess_regex = r'(?:ssr|vmess|vless|ss|hysteria2|trojan)://[^\s]*?(?=(?:ssr|vmess|vless|ss|hysteria2|trojan)://|$)'
            matches = re.findall(ssr_vmess_regex, line)
            if matches:
                nodes_array.extend(matches)
