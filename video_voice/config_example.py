"""
配置文件示例

复制此文件为 config.py 并填入你的实际配置参数
"""

# Bedrock配置
BEDROCK_REGION = "us-west-2"
BEDROCK_MODEL_ID = "us.amazon.nova-lite-v1:0"

# ComfyUI配置
# 请填入你的ComfyUI服务器地址和端口
COMFYUI_SERVER_URL = ""  # 例如: "your-server.com:8080"

# ComfyUI工作流JSON文件路径
# 请根据你的ComfyUI配置创建相应的工作流文件
COMFYUI_WORKFLOW_PATH = ""  # 例如: "workflows/img2video_workflow.json"

# GPT-SoVITS配置
# 请填入你的GPT-SoVITS SageMaker端点名称
GPT_SOVITS_ENDPOINT = ""  # 例如: "gpt-sovits-inference-2025-01-01-12-00-00-000"

# 参考音频路径（用于语音克隆）
# 可以是S3路径或本地路径
REFERENCE_AUDIO_PATH = ""  # 例如: "s3://your-bucket/reference-audio.mp3"

# 批处理配置
BATCH_SIZE = 3  # 每批处理的图像数量
MAX_IMAGES = 10  # 最大处理图像数量

# 输出配置
OUTPUT_VIDEO_FORMAT = "mp4"  # 输出视频格式
OUTPUT_AUDIO_FORMAT = "wav"  # 输出音频格式

# 视频生成参数
VIDEO_GENERATION_PARAMS = {
    "duration": 3.0,  # 每个视频片段的时长（秒）
    "fps": 24,        # 帧率
    "resolution": "1024x1024"  # 分辨率
}

# 音频生成参数
AUDIO_GENERATION_PARAMS = {
    "text_lang": "zh",           # 文本语言
    "prompt_lang": "zh",         # 提示语言
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

# 提示词模板
COMIC_ANALYSIS_PROMPT = """请仔细分析这张漫画图像，并以JSON格式返回以下信息（使用中文回答）：
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

# 系统提示词
SYSTEM_PROMPT = "你是一个专业的漫画分析师和视频制作专家，擅长从漫画图像中提取关键信息并转化为视频制作素材。请客观、详细地分析漫画内容。"

# 文件路径配置
PATHS = {
    "input_images": "input_images",
    "output_videos": "output_videos", 
    "output_audio": "output_audio",
    "final_videos": "final_videos",
    "temp": "temp",
    "logs": "logs"
}

# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/comic_video.log"
}

# 错误处理配置
ERROR_HANDLING = {
    "max_retries": 3,           # 最大重试次数
    "retry_delay": 5,           # 重试延迟（秒）
    "continue_on_error": True,  # 遇到错误时是否继续处理其他文件
    "save_partial_results": True  # 是否保存部分结果
}

# 性能优化配置
PERFORMANCE = {
    "parallel_processing": False,  # 是否启用并行处理
    "max_workers": 2,             # 最大工作线程数
    "memory_limit_mb": 4096,      # 内存限制（MB）
    "cleanup_temp_files": True    # 是否自动清理临时文件
}

# 质量控制配置
QUALITY_CONTROL = {
    "min_image_size": (512, 512),     # 最小图像尺寸
    "max_image_size": (2048, 2048),   # 最大图像尺寸
    "min_text_length": 5,             # 最小文本长度
    "max_text_length": 500,           # 最大文本长度
    "video_quality": "high",          # 视频质量: low, medium, high
    "audio_quality": "high"           # 音频质量: low, medium, high
}

# 调试配置
DEBUG = {
    "save_intermediate_results": False,  # 是否保存中间结果
    "verbose_logging": False,            # 是否启用详细日志
    "dry_run": False,                    # 是否只进行测试运行
    "skip_video_generation": False,     # 是否跳过视频生成（用于测试）
    "skip_audio_generation": False      # 是否跳过音频生成（用于测试）
}

# 验证配置函数
def validate_config():
    """
    验证配置是否完整和正确
    """
    errors = []
    
    if not COMFYUI_SERVER_URL:
        errors.append("COMFYUI_SERVER_URL 未设置")
    
    if not COMFYUI_WORKFLOW_PATH:
        errors.append("COMFYUI_WORKFLOW_PATH 未设置")
    
    if not GPT_SOVITS_ENDPOINT:
        errors.append("GPT_SOVITS_ENDPOINT 未设置")
    
    if not REFERENCE_AUDIO_PATH:
        errors.append("REFERENCE_AUDIO_PATH 未设置")
    
    if errors:
        print("❌ 配置验证失败:")
        for error in errors:
            print(f"  • {error}")
        return False
    
    print("✅ 配置验证通过")
    return True

# 获取配置函数
def get_config():
    """
    获取完整配置字典
    """
    return {
        "bedrock": {
            "region": BEDROCK_REGION,
            "model_id": BEDROCK_MODEL_ID
        },
        "comfyui": {
            "server_url": COMFYUI_SERVER_URL,
            "workflow_path": COMFYUI_WORKFLOW_PATH
        },
        "gpt_sovits": {
            "endpoint": GPT_SOVITS_ENDPOINT,
            "reference_audio": REFERENCE_AUDIO_PATH,
            "params": AUDIO_GENERATION_PARAMS
        },
        "processing": {
            "batch_size": BATCH_SIZE,
            "max_images": MAX_IMAGES
        },
        "video": VIDEO_GENERATION_PARAMS,
        "paths": PATHS,
        "logging": LOGGING_CONFIG,
        "error_handling": ERROR_HANDLING,
        "performance": PERFORMANCE,
        "quality": QUALITY_CONTROL,
        "debug": DEBUG
    }

if __name__ == "__main__":
    # 运行配置验证
    validate_config()
    
    # 显示配置摘要
    config = get_config()
    print("\n📋 配置摘要:")
    print(f"  • Bedrock区域: {config['bedrock']['region']}")
    print(f"  • ComfyUI服务器: {config['comfyui']['server_url'] or '未设置'}")
    print(f"  • GPT-SoVITS端点: {config['gpt_sovits']['endpoint'] or '未设置'}")
    print(f"  • 批处理大小: {config['processing']['batch_size']}")
    print(f"  • 最大图像数: {config['processing']['max_images']}")
