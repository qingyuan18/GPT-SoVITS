"""
漫画转视频配音工具模块

这个模块包含了漫画图像转视频配音的核心功能，
可以被Jupyter notebook或其他Python脚本导入使用。
"""

import base64
import boto3
import json
import time
import os
import requests
import urllib.request
import urllib.parse
import uuid
import subprocess
import io
import wave
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import numpy as np

class ComicVideoProcessor:
    """漫画转视频配音处理器"""
    
    def __init__(self, 
                 bedrock_region: str = "us-west-2",
                 bedrock_model_id: str = "us.amazon.nova-lite-v1:0",
                 comfyui_server_url: str = "",
                 comfyui_workflow_path: str = "",
                 gpt_sovits_endpoint: str = "",
                 reference_audio_path: str = "",
                 batch_size: int = 10,
                 max_images: int = 80):
        """
        初始化处理器
        
        Args:
            bedrock_region: Bedrock服务区域
            bedrock_model_id: Bedrock模型ID
            comfyui_server_url: ComfyUI服务器URL
            comfyui_workflow_path: ComfyUI工作流JSON文件路径
            gpt_sovits_endpoint: GPT-SoVITS端点名称
            reference_audio_path: 参考音频路径
            batch_size: 批处理大小
            max_images: 最大处理图像数量
        """
        self.bedrock_region = bedrock_region
        self.bedrock_model_id = bedrock_model_id
        self.comfyui_server_url = comfyui_server_url
        self.comfyui_workflow_path = comfyui_workflow_path
        self.gpt_sovits_endpoint = gpt_sovits_endpoint
        self.reference_audio_path = reference_audio_path
        self.batch_size = batch_size
        self.max_images = max_images
        
        # 初始化Bedrock客户端
        self.bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=self.bedrock_region,
        )
        
        # 创建必要的目录
        self._create_directories()
    
    def _create_directories(self):
        """创建必要的目录结构"""
        directories = [
            'input_images', 'output_videos', 'output_audio', 
            'final_videos', 'temp'
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def analyze_comic_images_batch(self, image_paths: List[str], batch_index: int = 0) -> Dict:
        """
        使用Bedrock Nova模型批量分析多张漫画图像内容，并选择最佳图像用于视频生成

        Args:
            image_paths: 图像文件路径列表
            batch_index: 批次索引

        Returns:
            包含分析结果和选中图像的字典
        """
        start_time = time.time()

        try:
            # 读取所有图像文件并编码为Base64
            image_contents = []
            for i, image_path in enumerate(image_paths):
                with open(image_path, "rb") as image_file:
                    binary_data = image_file.read()
                    base_64_encoded_data = base64.b64encode(binary_data)
                    base64_string = base_64_encoded_data.decode("utf-8")

                    # 添加图像到内容列表
                    image_contents.append({
                        "image": {
                            "format": "png",
                            "source": {"bytes": base64_string},
                        }
                    })

            # 漫画内容分析提示词（针对多图像）- 简化输出结构
            custom_prompt = f"""请仔细分析这{len(image_paths)}张漫画图像，并返回以下信息（使用中文回答）：

{{
  "overall_analysis": {{
    "story_flow": "整体故事流程和连贯性分析",
    "main_theme": "主要主题和情节发展",
    "character_development": "人物发展和关系变化"
  }},
  "selected_index": "选择为视频输入的图像序号（从0开始，对应提供的图像列表）",
  "video_prompt": "基于整个批次图像的完整视频生成的中文提示词，描述如何让选中的画面动起来",
  "combined_audio_script": "结合整个批次所有图像信息生成的完整配音文本"
}}

请分析所有图像的整体故事内容，选择最适合视频生成的一张图像，并提供整个批次的视频生成提示词和完整配音文本。"""

            # 定义系统提示
            system_list = [
                {
                    "text": "你是一个专业的漫画分析师和视频制作专家，擅长客观、详细地分析漫画内容，从多张漫画图像中提取关键信息、分析故事连贯性。"
                }
            ]

            # 构建用户消息内容（包含所有图像和文本）
            content_list = []

            # 添加所有图像
            for image_content in image_contents:
                content_list.append(image_content)

            # 添加分析提示
            content_list.append({
                "text": custom_prompt
            })

            # 定义用户消息
            message_list = [
                {
                    "role": "user",
                    "content": content_list
                }
            ]

            # 配置推理参数（增加token数量以支持多图像分析）
            inf_params = {"maxTokens": 8000, "topP": 0.1, "topK": 20, "temperature": 0.3}

            native_request = {
                "schemaVersion": "messages-v1",
                "messages": message_list,
                "system": system_list,
                "inferenceConfig": inf_params,
            }

            # 调用Bedrock API
            api_start_time = time.time()
            response = self.bedrock_client.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(native_request)
            )
            model_response = json.loads(response["body"].read())
            api_end_time = time.time()

            # 计算时延
            total_latency = api_end_time - start_time
            api_latency = api_end_time - api_start_time

            # 提取响应内容
            content_text = model_response["output"]["message"]["content"][0]["text"]

            # 尝试解析JSON响应
            try:
                parsed_content = json.loads(content_text)

                # 验证响应结构
                if 'selected_index' in parsed_content:
                    selected_index = parsed_content['selected_index']
                    # 验证索引是否有效
                    if isinstance(selected_index, int) and 0 <= selected_index < len(image_paths):
                        selected_image_path = image_paths[selected_index]
                    else:
                        # 如果索引无效，选择第一张图像
                        selected_index = 0
                        selected_image_path = image_paths[0]
                        print(f"⚠️ 选择的图像索引无效，使用第一张图像")
                else:
                    # 如果没有选择信息，默认选择第一张
                    selected_index = 0
                    selected_image_path = image_paths[0]
                    parsed_content['selected_index'] = selected_index
                    print(f"⚠️ 未找到图像选择信息，使用第一张图像")

            except json.JSONDecodeError:
                # 如果不是有效JSON，创建默认结构化响应
                selected_index = 0
                selected_image_path = image_paths[0]
                parsed_content = {
                    "overall_analysis": {
                        "story_flow": "解析失败",
                        "main_theme": content_text[:100],
                        "character_development": "未识别"
                    },
                    "selected_index": selected_index,
                    "video_prompt": "animate the comic scene",
                    "combined_audio_script": content_text[:300],
                    "raw_response": content_text
                }

            return {
                'success': True,
                'image_paths': image_paths,
                'selected_image_path': selected_image_path,
                'selected_image_index': selected_index,
                'batch_index': batch_index,
                'analysis_result': parsed_content,
                'raw_response': content_text,
                'model_id': self.bedrock_model_id,
                'usage': model_response.get('usage', {}),
                'latency': {
                    'total_ms': round(total_latency * 1000, 2),
                    'api_ms': round(api_latency * 1000, 2)
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'image_paths': image_paths,
                'selected_image_path': image_paths[0] if image_paths else None,
                'selected_image_index': 0,
                'batch_index': batch_index,
                'error': str(e),
                'latency': {
                    'total_ms': round((time.time() - start_time) * 1000, 2),
                    'api_ms': 0
                },
                'timestamp': datetime.now().isoformat()
            }

    def analyze_comic_image_content(self, image_path: str, batch_index: int = 0) -> Dict:
        """
        单张图像分析的兼容方法（调用批量分析）

        Args:
            image_path: 图像文件路径
            batch_index: 批次索引

        Returns:
            包含分析结果的字典
        """
        # 调用批量分析方法处理单张图像
        result = self.analyze_comic_images_batch([image_path], batch_index)

        if result.get('success') and result.get('analysis_result'):
            # 转换为单图像格式以保持兼容性
            analysis = result['analysis_result']
            # 新的简化结构直接使用分析结果
            return {
                'success': True,
                'file_path': image_path,
                'batch_index': batch_index,
                'analysis_result': analysis,
                'raw_response': result.get('raw_response', ''),
                'model_id': result.get('model_id', ''),
                'usage': result.get('usage', {}),
                'latency': result.get('latency', {}),
                'timestamp': result.get('timestamp', '')
            }

        # 如果批量分析失败，返回错误
        return {
            'success': False,
            'file_path': image_path,
            'batch_index': batch_index,
            'error': result.get('error', 'Unknown error'),
            'latency': result.get('latency', {}),
            'timestamp': result.get('timestamp', '')
        }

    def get_comic_images_from_directory(self, directory_path: str) -> List[str]:
        """
        从目录中获取所有支持的图像文件
        
        Args:
            directory_path: 目录路径
        
        Returns:
            图像文件路径列表
        """
        supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        
        image_files = []
        
        if not os.path.exists(directory_path):
            print(f"❌ 目录不存在: {directory_path}")
            return image_files
        
        print(f"📂 扫描目录: {directory_path}")
        
        for file in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in supported_extensions:
                    image_files.append(file_path)
                    print(f"  ✅ 找到图像: {file}")
        
        print(f"📊 总共找到 {len(image_files)} 个图像文件")
        return sorted(image_files)

    def batch_analyze_comic_images(self, directory_path: str, max_files: int = None) -> List[Dict]:
        """
        批量分析目录中的漫画图像（使用多图像API）

        Args:
            directory_path: 目录路径
            max_files: 最大处理文件数

        Returns:
            分析结果列表（转换为单图像格式以保持兼容性）
        """
        # 获取目录中的所有图像文件
        image_files = self.get_comic_images_from_directory(directory_path)

        if not image_files:
            print("❌ 目录中没有找到支持的图像文件")
            return []

        # 限制处理文件数量
        if max_files and len(image_files) > max_files:
            print(f"⚠️ 文件数量超过限制，只处理前 {max_files} 个文件")
            image_files = image_files[:max_files]

        results = []
        selected_images_info = []  # 记录每批次选中的图像信息
        total_start_time = time.time()

        print(f"\n🚀 开始批量分析 {len(image_files)} 个图像（多图像模式）...\n")

        # 按批次处理（每批次包含多张图像）
        for batch_start in range(0, len(image_files), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(image_files))
            batch_files = image_files[batch_start:batch_end]

            print(f"📦 处理批次 {batch_start//self.batch_size + 1}: 图像 {batch_start+1}-{batch_end}")
            print(f"📁 批次包含图像:")
            for i, file_path in enumerate(batch_files):
                relative_path = os.path.relpath(file_path, directory_path)
                print(f"  {i+1}. {relative_path}")

            try:
                # 调用多图像分析API
                result = self.analyze_comic_images_batch(batch_files, batch_start//self.batch_size)

                if result.get('success'):
                    analysis = result['analysis_result']

                    selected_path = result.get('selected_image_path', '')
                    selected_index = result.get('selected_image_index', 0)

                    print(f"  ✅ 批次分析完成")
                    print(f"  🔑 选中图像: 第{selected_index + 1}张 - {os.path.basename(selected_path)}")

                    # 显示整体分析信息
                    if 'overall_analysis' in analysis:
                        overall = analysis['overall_analysis']
                        if 'main_theme' in overall:
                            print(f"  🎭 主要主题: {overall['main_theme']}")

                    # 显示视频提示词
                    if 'video_prompt' in analysis:
                        video_prompt = analysis['video_prompt']
                        print(f"  🎬 视频提示: {video_prompt}")

                    # 显示配音文本
                    if 'combined_audio_script' in analysis:
                        audio_script = analysis['combined_audio_script']
                        print(f"  🎙️ 配音文本: {audio_script[:100]}{'...' if len(audio_script) > 100 else ''}")

                    # 直接使用简化的分析结果（新的JSON结构已经是扁平化的）
                    selected_analysis = analysis.copy()

                    # 创建兼容格式的结果
                    converted_result = {
                        'success': True,
                        'file_path': selected_path,
                        'batch_index': batch_start//self.batch_size,
                        'analysis_result': selected_analysis,
                        'raw_response': result.get('raw_response', ''),
                        'model_id': result.get('model_id', ''),
                        'usage': result.get('usage', {}),
                        'latency': result.get('latency', {}),
                        'timestamp': result.get('timestamp', ''),
                        # 新增字段
                        'is_selected_from_batch': True,
                        'batch_image_paths': batch_files,
                        'batch_analysis': analysis
                    }

                    results.append(converted_result)

                    # 记录选中的图像信息
                    selected_images_info.append({
                        'batch_index': batch_start//self.batch_size,
                        'selected_image_path': selected_path,
                        'selected_image_index': selected_index,
                        'batch_files': batch_files,
                        'analysis': selected_analysis
                    })
                else:
                    print(f"  ❌ 批次分析失败: {result.get('error', 'Unknown error')}")
                    # 处理失败的批次
                    converted_result = {
                        'success': False,
                        'file_path': batch_files[0] if batch_files else None,
                        'batch_index': batch_start//self.batch_size,
                        'error': result.get('error', 'Unknown error'),
                        'latency': result.get('latency', {}),
                        'timestamp': result.get('timestamp', ''),
                        'is_selected_from_batch': False,
                        'batch_image_paths': batch_files
                    }
                    results.append(converted_result)

                print(f"  ⏱️ 耗时: {result.get('latency', {}).get('total_ms', 0):.2f}ms\n")

            except Exception as e:
                print(f"❌ 处理批次失败: {str(e)}")
                converted_result = {
                    'success': False,
                    'file_path': batch_files[0] if batch_files else None,
                    'batch_index': batch_start//self.batch_size,
                    'error': str(e),
                    'is_selected_from_batch': False,
                    'batch_image_paths': batch_files
                }
                results.append(converted_result)

            # 避免API限流
            if batch_end < len(image_files):
                print("⏱️ 批次间休息 3 秒...")
                time.sleep(3)

        total_time = time.time() - total_start_time

        # 打印批量处理统计
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]

        print("📊 批量处理统计:")
        print(f"  • 处理目录: {directory_path}")
        print(f"  • 总图像数: {len(image_files)}")
        print(f"  • 处理批次: {len(results)}")
        print(f"  • 成功批次: {len(successful)}")
        print(f"  • 失败批次: {len(failed)}")
        print(f"  • 选中图像: {len(selected_images_info)}")
        print(f"  • 总耗时: {total_time:.2f}秒")

        if successful:
            avg_latency = sum(r.get('latency', {}).get('total_ms', 0) for r in successful) / len(successful)
            print(f"  • 平均延迟: {avg_latency:.2f}ms")

        # 保存选中图像信息
        if selected_images_info:
            selected_images_file = os.path.join('temp', 'selected_images_info.json')
            with open(selected_images_file, 'w', encoding='utf-8') as f:
                json.dump(selected_images_info, f, ensure_ascii=False, indent=2)
            print(f"  • 选中图像信息已保存: {selected_images_file}")

        return results

    def check_dependencies(self) -> bool:
        """
        检查系统依赖
        
        Returns:
            是否所有依赖都满足
        """
        print("🔧 检查系统依赖:")
        all_ok = True
        
        # 检查ffmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("  ✅ ffmpeg 已安装")
            else:
                print("  ❌ ffmpeg 未正确安装")
                all_ok = False
        except FileNotFoundError:
            print("  ❌ ffmpeg 未找到")
            all_ok = False
        
        # 检查ffprobe
        try:
            result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("  ✅ ffprobe 已安装")
            else:
                print("  ❌ ffprobe 未正确安装")
                all_ok = False
        except FileNotFoundError:
            print("  ❌ ffprobe 未找到")
            all_ok = False
        
        # 检查Python包
        required_packages = ['boto3', 'requests']
        for package in required_packages:
            try:
                __import__(package)
                print(f"  ✅ {package} 已安装")
            except ImportError:
                print(f"  ❌ {package} 未安装")
                all_ok = False
        
        return all_ok

    def image_to_base64(self, image_path: str) -> Optional[str]:
        """
        将图像文件转换为Base64编码

        Args:
            image_path: 图像文件路径

        Returns:
            Base64编码字符串，失败时返回None
        """
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                base64_encoded = base64.b64encode(image_data).decode('utf-8')
                return base64_encoded
        except IOError:
            print(f"无法读取文件: {image_path}")
            return None

    def queue_prompt(self, prompt, server_url):
        """
        向ComfyUI服务器提交任务
        """
        client_id = str(uuid.uuid4())
        p = {"prompt": prompt, "client_id": client_id}
        data = json.dumps(p).encode('utf-8')
        url = f"{server_url}/prompt"
        req = urllib.request.Request(url, data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def get_video_by_prompt_id(self, prompt_id, server_url):
        """
        根据prompt_id获取生成的视频
        """
        def get_history(prompt_id):
            with urllib.request.urlopen(f"{server_url}/history/{prompt_id}") as response:
                return json.loads(response.read())

        def get_video(filename, subfolder, folder_type):
            data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
            url_values = urllib.parse.urlencode(data)
            with urllib.request.urlopen(f"{server_url}/view?{url_values}") as response:
                return response.read()

        output_videos = {}
        while True:
            try:
                history = get_history(prompt_id)[prompt_id]
                for node_id in history['outputs']:
                    node_output = history['outputs'][node_id]
                    # 视频输出分支
                    if 'gifs' in node_output:
                        videos_output = []
                        for video in node_output['gifs']:
                            video_data = get_video(video['filename'], video['subfolder'], video['type'])
                            videos_output.append(video_data)
                        output_videos[node_id] = videos_output
                break
            except Exception as e:
                print(f"等待执行历史: {e}")
                time.sleep(5)
                continue

        return output_videos

    def generate_video_from_image(self, image_path: str, video_prompt: str, output_path: str) -> bool:
        """
        使用ComfyUI从图像生成视频

        Args:
            image_path: 输入图像路径
            video_prompt: 视频生成提示词
            output_path: 输出视频路径

        Returns:
            是否成功生成视频
        """
        if not self.comfyui_server_url or not self.comfyui_workflow_path:
            print("❌ ComfyUI配置未完成，请设置COMFYUI_SERVER_URL和COMFYUI_WORKFLOW_PATH")
            return False

        try:
            # 读取workflow模板
            with open(self.comfyui_workflow_path, 'r') as f:
                workflow = json.load(f)

            # 将图像转换为base64
            base64_image = self.image_to_base64(image_path)
            if not base64_image:
                return False

            # 修改workflow中的参数（这里需要根据实际的workflow结构调整）
            # 假设workflow中有图像输入节点和文本提示节点
            # 根据实际workflow调整这些节点ID和参数名

            # 示例：设置图像输入（需要根据实际workflow调整）
            if '29' in workflow:  # 替换为实际的节点ID
                workflow['29']['inputs']['image'] = base64_image

            # 示例：设置文本提示（需要根据实际workflow调整）
            if '33' in workflow:  # 替换为实际的节点ID
                workflow['33']['inputs']['text'] = video_prompt

            print(f"🎬 开始生成视频: {os.path.basename(image_path)}")
            print(f"📝 视频提示词: {video_prompt}")

            # 提交任务
            result = self.queue_prompt(workflow, self.comfyui_server_url)
            prompt_id = result['prompt_id']
            print(f"📋 任务ID: {prompt_id}")

            # 获取生成的视频
            output_videos = self.get_video_by_prompt_id(prompt_id, self.comfyui_server_url)

            if output_videos:
                # 保存第一个生成的视频
                for node_id, videos in output_videos.items():
                    if videos:
                        with open(output_path, 'wb') as f:
                            f.write(videos[0])
                        print(f"✅ 视频已保存: {output_path}")
                        return True

            print("❌ 未生成视频")
            return False

        except Exception as e:
            print(f"❌ 视频生成失败: {str(e)}")
            return False

    def upsert(self, lst, new_dict):
        """
        更新或插入字典到列表中
        """
        for i, item in enumerate(lst):
            if new_dict['index'] == i:
                lst[i] = new_dict
                return lst
        lst.append(new_dict)
        return lst

    def invoke_gpt_sovits_endpoint(self, smr_client, endpoint_name, request):
        """
        调用GPT-SoVITS端点生成语音
        """
        content_type = "application/json"
        payload = json.dumps(request, ensure_ascii=False)

        response_model = smr_client.invoke_endpoint_with_response_stream(
            EndpointName=endpoint_name,
            ContentType=content_type,
            Body=payload,
        )

        result = []
        print(f"📡 响应元数据: {response_model['ResponseMetadata']}")
        event_stream = iter(response_model['Body'])
        index = 0
        chunk_bytes = None

        try:
            while True:
                event = next(event_stream)
                eventChunk = event['PayloadPart']['Bytes']
                chunk_dict = {}
                if index == 0:
                    print("📦 收到第一个音频块")
                    chunk_dict['first_chunk'] = True
                    chunk_dict['bytes'] = eventChunk
                    chunk_bytes = eventChunk
                    chunk_dict['last_chunk'] = False
                    chunk_dict['index'] = index
                else:
                    chunk_dict['first_chunk'] = False
                    chunk_dict['bytes'] = eventChunk
                    chunk_bytes = eventChunk
                    chunk_dict['last_chunk'] = False
                    chunk_dict['index'] = index
                print(f"📦 音频块长度: {len(chunk_dict['bytes'])}")
                result.append(chunk_dict)
                index += 1
        except StopIteration:
            print("✅ 所有音频块处理完成")
            chunk_dict = {}
            chunk_dict['first_chunk'] = False
            chunk_dict['bytes'] = chunk_bytes
            chunk_dict['last_chunk'] = True
            chunk_dict['index'] = index-1
            result = self.upsert(result, chunk_dict)

        return result

    def generate_audio_from_text(self, output_path: str, prompt_text: str = None, reference_text: str = None) -> bool:
        """
        使用GPT-SoVITS从文本生成语音

        Args:
            output_path: 输出音频文件路径
            prompt_text: 提示文本（可选）
            reference_text: 参考文本（可选）

        Returns:
            是否成功生成音频
        """
        if not self.gpt_sovits_endpoint or not self.reference_audio_path:
            print("❌ GPT-SoVITS配置未完成，请设置GPT_SOVITS_ENDPOINT和REFERENCE_AUDIO_PATH")
            return False

        try:
            runtime_sm_client = boto3.client(service_name="sagemaker-runtime")

            # 使用传入的reference_text，如果没有则使用默认值
            ref_text = reference_text or "它包括以下几个主要方面:SAP系统管理包括SAP系统实例的安装、启动、监控、备份、升级等日常管理任务。Basis团队负责保证系统的正常运行。"

            # 构建请求数据
            data = {
                "text": ref_text,
                "text_lang": "zh",
                "ref_audio_path": self.reference_audio_path,
                "prompt_lang": "zh",
                "prompt_text": prompt_text,
                "top_k": 5,
                "top_p": 1.0,
                "temperature": 0.7,
                "text_split_method": "cut5",
                "batch_size": 1,
                "batch_threshold": 0.75,
                "split_bucket": True,
                "speed_factor": 1.0,
                "fragment_interval": 0.3,
                "seed": -1,
                "media_type": "wav",
                "streaming_mode": False,
                "parallel_infer": True,
                "repetition_penalty": 1.35,
                "sample_steps": 32,
                "super_sampling": False
            }

            print(f"🔊 开始生成语音")
            print(f"📝 文本内容: {prompt_text[:100] if prompt_text else 'None'}{'...' if prompt_text and len(prompt_text) > 100 else ''}")

            # 调用GPT-SoVITS端点
            response = self.invoke_gpt_sovits_endpoint(runtime_sm_client, self.gpt_sovits_endpoint, data)

            # 合并音频数据
            audio_data = b''.join(chunk['bytes'] for chunk in response)

            # 保存音频文件
            with open(output_path, 'wb') as f:
                f.write(audio_data)

            print(f"✅ 音频已保存: {output_path}")
            return True

        except Exception as e:
            print(f"❌ 语音生成失败: {str(e)}")
            return False

    def merge_video_audio(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """
        合并视频和音频文件

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径

        Returns:
            是否成功合并
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-strict', 'experimental',
                '-y',  # 覆盖输出文件
                output_path
            ]

            print(f"🎞️ 合并视频和音频")
            print(f"📹 视频: {os.path.basename(video_path)}")
            print(f"🔊 音频: {os.path.basename(audio_path)}")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ 合并完成: {output_path}")
                return True
            else:
                print(f"❌ 合并失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 合并过程出错: {str(e)}")
            return False

    def add_subtitles_to_video(self, video_path: str, subtitle_text: str, output_path: str,
                              font_size: int = 10, font_color: str = 'white',
                              position: str = 'bottom', font_file: str = './yahei.ttf') -> bool:
        """
        为视频添加字幕

        Args:
            video_path: 输入视频路径
            subtitle_text: 字幕文本
            output_path: 输出视频路径
            font_size: 字体大小 (默认10)
            font_color: 字体颜色
            position: 字幕位置 ('bottom', 'top', 'center')
            font_file: 字体文件路径

        Returns:
            是否成功添加字幕
        """
        try:
            from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
            import shutil

            # 设置FFmpeg环境变量
            if 'IMAGEIO_FFMPEG_EXE' not in os.environ:
                ffmpeg_path = shutil.which('ffmpeg')
                if ffmpeg_path:
                    os.environ['IMAGEIO_FFMPEG_EXE'] = ffmpeg_path

            # 检查字体文件
            if not os.path.exists(font_file):
                print(f"⚠️ 字体文件不存在: {font_file}，使用默认字体")
                font_file = None

            # 加载视频
            video = VideoFileClip(video_path)

            # 计算字幕位置
            if position == 'bottom':
                subtitle_position = ('center', video.h - 30)
            elif position == 'top':
                subtitle_position = ('center', 20)
            else:  # center
                subtitle_position = ('center', 'center')

            # 创建字幕文本片段
            if font_file:
                subtitle_clip = TextClip(
                    subtitle_text,
                    fontsize=font_size,
                    color=font_color,
                    font=font_file
                ).set_position(subtitle_position).set_duration(video.duration)
            else:
                subtitle_clip = TextClip(
                    subtitle_text,
                    fontsize=font_size,
                    color=font_color
                ).set_position(subtitle_position).set_duration(video.duration)

            # 合成视频和字幕
            final_video = CompositeVideoClip([video, subtitle_clip])

            print(f"📝 添加字幕到视频")
            print(f"📹 输入视频: {os.path.basename(video_path)}")
            print(f"💬 字幕内容: {subtitle_text[:50]}{'...' if len(subtitle_text) > 50 else ''}")

            # 写入输出文件
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp_audio.m4a',
                remove_temp=True,
                verbose=False,
                logger=None
            )

            # 清理资源
            video.close()
            subtitle_clip.close()
            final_video.close()

            print(f"✅ 字幕视频已保存: {output_path}")
            return True

        except Exception as e:
            print(f"❌ 添加字幕失败: {str(e)}")
            return False

    def merge_video_audio_with_subtitles(self, video_path: str, audio_path: str,
                                       subtitle_text: str, output_path: str) -> bool:
        """
        合并视频、音频并添加字幕
        """
        try:
            import uuid

            # 临时文件路径
            temp_video_with_audio = os.path.join('temp', f'temp_merged_{uuid.uuid4().hex[:8]}.mp4')

            # 确保temp目录存在
            os.makedirs('temp', exist_ok=True)

            # 第一步：合并视频和音频
            if not self.merge_video_audio(video_path, audio_path, temp_video_with_audio):
                return False

            # 第二步：添加字幕
            success = self.add_subtitles_to_video(temp_video_with_audio, subtitle_text, output_path)

            # 保留临时文件用于troubleshooting
            if os.path.exists(temp_video_with_audio):
                print(f"💾 保留临时文件用于调试: {temp_video_with_audio}")
                # os.remove(temp_video_with_audio)  # 注释掉删除操作

            return success

        except Exception as e:
            print(f"❌ 合并视频音频并添加字幕失败: {str(e)}")
            return False

    def concatenate_videos(self, video_paths: List[str], output_path: str) -> bool:
        """
        拼接多个视频文件

        Args:
            video_paths: 视频文件路径列表
            output_path: 输出文件路径

        Returns:
            是否成功拼接
        """
        if not video_paths:
            print("❌ 没有视频文件需要拼接")
            return False

        if len(video_paths) == 1:
            # 只有一个视频，直接复制
            try:
                import shutil
                shutil.copy2(video_paths[0], output_path)
                print(f"✅ 单个视频已复制: {output_path}")
                return True
            except Exception as e:
                print(f"❌ 复制视频失败: {str(e)}")
                return False

        try:
            # 创建临时文件列表
            temp_list_file = os.path.join('temp', 'video_list.txt')
            with open(temp_list_file, 'w') as f:
                for video_path in video_paths:
                    # 使用绝对路径避免路径问题
                    abs_path = os.path.abspath(video_path)
                    f.write(f"file '{abs_path}'\\n")

            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', temp_list_file,
                '-c', 'copy',
                '-y',  # 覆盖输出文件
                output_path
            ]

            print(f"🎬 拼接 {len(video_paths)} 个视频文件")
            for i, path in enumerate(video_paths, 1):
                print(f"  {i}. {os.path.basename(path)}")

            result = subprocess.run(cmd, capture_output=True, text=True)

            # 清理临时文件
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)

            if result.returncode == 0:
                print(f"✅ 视频拼接完成: {output_path}")
                return True
            else:
                print(f"❌ 视频拼接失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 拼接过程出错: {str(e)}")
            return False

    def get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长（秒）

        Args:
            video_path: 视频文件路径

        Returns:
            视频时长（秒）
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                info = json.loads(result.stdout)
                duration = float(info['format']['duration'])
                return duration
            else:
                print(f"❌ 获取视频时长失败: {result.stderr}")
                return 0.0

        except Exception as e:
            print(f"❌ 获取视频时长出错: {str(e)}")
            return 0.0



    def process_comic_to_video_voice(self, input_directory: str) -> str:
        """
        完整的漫画转视频配音流程

        Args:
            input_directory: 输入漫画图像目录

        Returns:
            最终输出视频路径
        """
        print("🚀 开始漫画转视频配音流程")
        print("="*60)

        # 步骤1: 批量分析漫画图像
        print("\n📊 步骤1: 分析漫画图像内容")
        analysis_results = self.batch_analyze_comic_images(input_directory, self.max_images)

        if not analysis_results:
            print("❌ 没有成功分析的图像")
            return None

        # 过滤成功的分析结果
        successful_results = [r for r in analysis_results if r.get('success')]
        if not successful_results:
            print("❌ 没有成功分析的图像")
            return None

        print(f"✅ 成功分析 {len(successful_results)} 张图像")

        # 步骤2: 生成视频
        print("\n🎬 步骤2: 生成视频")
        video_files = []
        audio_scripts = []

        for i, result in enumerate(successful_results):
            analysis = result['analysis_result']
            image_path = result['file_path']

            # 生成视频文件名
            video_filename = f"video_{i:03d}.mp4"
            video_path = os.path.join('output_videos', video_filename)

            # 获取视频提示词
            video_prompt = analysis.get('video_prompt', 'animate the comic scene')

            print(f"\n🎥 生成视频 {i+1}/{len(successful_results)}")
            if self.generate_video_from_image(image_path, video_prompt, video_path):
                video_files.append(video_path)
                # 收集音频脚本（使用新的combined_audio_script字段）
                audio_script = analysis.get('combined_audio_script', '')
                if audio_script and audio_script.strip():
                    audio_scripts.append(audio_script)
                else:
                    audio_scripts.append(f"第{i+1}个场景")
            else:
                print(f"⚠️ 视频 {i+1} 生成失败，跳过")

        if not video_files:
            print("❌ 没有成功生成的视频")
            return None

        print(f"✅ 成功生成 {len(video_files)} 个视频")

        # 步骤3: 生成语音
        print("\n🔊 步骤3: 生成语音")
        audio_files = []

        for i, script in enumerate(audio_scripts):
            audio_filename = f"audio_{i:03d}.wav"
            audio_path = os.path.join('output_audio', audio_filename)

            print(f"\n🎙️ 生成语音 {i+1}/{len(audio_scripts)}")
            if self.generate_audio_from_text(output_path=audio_path, prompt_text=script):
                audio_files.append(audio_path)
            else:
                print(f"⚠️ 语音 {i+1} 生成失败，跳过")
                audio_files.append(None)

        print(f"✅ 成功生成 {len([a for a in audio_files if a])} 个语音文件")

        # 步骤4: 合并视频、音频并添加字幕
        print("\n🎞️ 步骤4: 合并视频、音频并添加字幕")
        final_video_files = []

        for i, (video_path, audio_path) in enumerate(zip(video_files, audio_files)):
            final_filename = f"final_{i:03d}.mp4"
            final_path = os.path.join('final_videos', final_filename)

            # 获取对应的字幕文本
            subtitle_text = audio_scripts[i] if i < len(audio_scripts) else ""

            if audio_path and os.path.exists(audio_path):
                print(f"\n🎬 合并视频音频并添加字幕 {i+1}/{len(video_files)}")
                if self.merge_video_audio_with_subtitles(video_path, audio_path, subtitle_text, final_path):
                    final_video_files.append(final_path)
                else:
                    print(f"⚠️ 合并失败，尝试仅添加字幕")
                    # 如果合并失败，尝试只添加字幕
                    if subtitle_text and self.add_subtitles_to_video(video_path, subtitle_text, final_path):
                        final_video_files.append(final_path)
                    else:
                        print(f"⚠️ 字幕添加也失败，使用原视频")
                        final_video_files.append(video_path)
            else:
                print(f"⚠️ 没有对应音频，仅添加字幕")
                if subtitle_text and self.add_subtitles_to_video(video_path, subtitle_text, final_path):
                    final_video_files.append(final_path)
                else:
                    print(f"⚠️ 没有字幕文本，使用原视频")
                    final_video_files.append(video_path)

        # 步骤5: 拼接所有视频
        print("\n🎬 步骤5: 拼接最终视频")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_output = f"comic_video_{timestamp}.mp4"

        if self.concatenate_videos(final_video_files, final_output):
            print(f"\n🎉 流程完成！")
            print(f"📁 最终视频: {final_output}")

            # 显示统计信息
            total_duration = sum(self.get_video_duration(vf) for vf in final_video_files if os.path.exists(vf))
            print(f"⏱️ 总时长: {total_duration:.2f} 秒")
            print(f"📊 处理统计:")
            print(f"  • 输入图像: {len(analysis_results)}")
            print(f"  • 生成视频: {len(video_files)}")
            print(f"  • 生成语音: {len([a for a in audio_files if a])}")

            return final_output
        else:
            print("❌ 最终视频拼接失败")
            return None

    def cleanup_temp_files(self):
        """
        清理临时文件（保留temp_merged文件用于调试）
        """
        import glob

        print("🧹 清理临时文件...")

        # 清理其他临时文件，但保留temp_merged文件
        temp_patterns = [
            'temp_audio.m4a',
            'temp/video_list.txt'
        ]

        cleaned_count = 0
        for pattern in temp_patterns:
            if os.path.exists(pattern):
                try:
                    os.remove(pattern)
                    print(f"🗑️ 已删除: {pattern}")
                    cleaned_count += 1
                except Exception as e:
                    print(f"⚠️ 删除失败 {pattern}: {str(e)}")

        print(f"✅ 清理完成，共删除 {cleaned_count} 个临时文件")
        print("💾 保留 temp/temp_merged_*.mp4 文件用于调试")

    def cleanup_all_temp_files(self):
        """
        清理所有临时文件（包括temp_merged文件）
        """
        import glob

        print("🧹 清理所有临时文件...")

        # 清理temp目录中的所有临时文件
        temp_patterns = [
            'temp/temp_merged_*.mp4',
            'temp_audio.m4a',
            'temp/video_list.txt'
        ]

        cleaned_count = 0
        for pattern in temp_patterns:
            files = glob.glob(pattern)
            for file_path in files:
                try:
                    os.remove(file_path)
                    print(f"🗑️ 已删除: {file_path}")
                    cleaned_count += 1
                except Exception as e:
                    print(f"⚠️ 删除失败 {file_path}: {str(e)}")

        print(f"✅ 清理完成，共删除 {cleaned_count} 个临时文件")


def create_sample_workflow():
    """
    创建示例ComfyUI工作流文件
    """
    sample_workflow = {
        "1": {
            "inputs": {
                "image": "",  # 这里会被替换为base64图像
                "upload": "image"
            },
            "class_type": "LoadImage",
            "_meta": {
                "title": "Load Image"
            }
        },
        "2": {
            "inputs": {
                "text": "",  # 这里会被替换为视频提示词
                "clip": ["4", 0]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "CLIP Text Encode (Prompt)"
            }
        },
        # 更多节点...
        # 注意：这只是一个示例结构，实际的workflow需要根据ComfyUI的具体配置来调整
    }

    workflow_path = "video_voice/sample_workflow.json"
    with open(workflow_path, 'w') as f:
        json.dump(sample_workflow, f, indent=2)

    print(f"📄 示例工作流已创建: {workflow_path}")
    print("⚠️ 请根据实际的ComfyUI配置修改此文件")

    return workflow_path



