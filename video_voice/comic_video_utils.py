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
                 batch_size: int = 3,
                 max_images: int = 10):
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
    
    def analyze_comic_image_content(self, image_path: str, batch_index: int = 0) -> Dict:
        """
        使用Bedrock Nova模型分析漫画图像内容
        
        Args:
            image_path: 图像文件路径
            batch_index: 批次索引
        
        Returns:
            包含分析结果的字典
        """
        start_time = time.time()
        
        try:
            # 读取图像文件并编码为Base64
            with open(image_path, "rb") as image_file:
                binary_data = image_file.read()
                base_64_encoded_data = base64.b64encode(binary_data)
                base64_string = base_64_encoded_data.decode("utf-8")
            
            # 漫画内容分析提示词
            custom_prompt = """请仔细分析这张漫画图像，并以JSON格式返回以下信息（使用中文回答）：
{
  "scene_description": "场景的详细描述，包括背景、环境、氛围",
  "characters": "人物描述，包括外观、表情、动作、服装",
  "dialogue_text": "图中的对话文字或旁白文字（如果有的话）",
  "story_content": "这一格漫画想要表达的故事内容或情节",
  "visual_style": "画面风格描述，如色彩、线条、构图等",
  "emotion_tone": "整体情感基调（如欢快、紧张、温馨、悲伤等）",
  "video_prompt": "适合用于图生视频的英文提示词，描述如何让这个画面动起来",
  "audio_script": "适合配音的文本内容，可以是对话、旁白或场景描述",
  "key_elements": "画面中的关键元素列表"
}"""
            
            # 定义系统提示
            system_list = [
                {
                    "text": "你是一个专业的漫画分析师和视频制作专家，擅长从漫画图像中提取关键信息并转化为视频制作素材。请客观、详细地分析漫画内容。"
                }
            ]
            
            # 定义用户消息
            message_list = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "png",
                                "source": {"bytes": base64_string},
                            }
                        },
                        {
                            "text": custom_prompt
                        },
                    ],
                }
            ]
            
            # 配置推理参数
            inf_params = {"maxTokens": 800, "topP": 0.1, "topK": 20, "temperature": 0.3}
            
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
            except json.JSONDecodeError:
                # 如果不是有效JSON，创建结构化响应
                parsed_content = {
                    "scene_description": content_text,
                    "characters": "未识别",
                    "dialogue_text": "",
                    "story_content": content_text,
                    "visual_style": "未识别",
                    "emotion_tone": "未识别",
                    "video_prompt": "animate the comic scene",
                    "audio_script": content_text[:200],
                    "key_elements": [],
                    "raw_response": content_text
                }
            
            return {
                'success': True,
                'file_path': image_path,
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
                'file_path': image_path,
                'batch_index': batch_index,
                'error': str(e),
                'latency': {
                    'total_ms': round((time.time() - start_time) * 1000, 2),
                    'api_ms': 0
                },
                'timestamp': datetime.now().isoformat()
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

    def cleanup_temp_files(self):
        """
        清理临时文件和目录
        """
        import shutil

        temp_dirs = ['temp', 'output_videos', 'output_audio']
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    os.makedirs(temp_dir, exist_ok=True)
                    print(f"🧹 已清理: {temp_dir}")
                except Exception as e:
                    print(f"❌ 清理失败 {temp_dir}: {e}")


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
