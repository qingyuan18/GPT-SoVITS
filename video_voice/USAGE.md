# 使用指南

## 🚀 快速开始

### 1. 检查系统依赖

#### 系统依赖
```bash
# 安装ffmpeg (macOS)
brew install ffmpeg

# 安装ffmpeg (Ubuntu)
sudo apt update
sudo apt install ffmpeg

# 安装ffmpeg (Windows)
# 下载并安装 https://ffmpeg.org/download.html
```

#### Python依赖
```bash
pip install boto3 requests pydub numpy
```

```bash
cd video_voice
python3 run_comic_video.py --check-deps
```

如果看到 "✅ 所有依赖检查通过"，说明系统环境准备就绪。

### 2. 准备配置文件

复制示例配置文件并填入你的参数：

```bash
cp config_example.py config.py
```

编辑 `config.py` 文件，填入以下必要参数：

```python
# ComfyUI配置
COMFYUI_SERVER_URL = "your-comfyui-server.com:8080"
COMFYUI_WORKFLOW_PATH = "sample_workflow.json"  # 或你的自定义工作流

# GPT-SoVITS配置  
GPT_SOVITS_ENDPOINT = "your-gpt-sovits-endpoint-name"
REFERENCE_AUDIO_PATH = "s3://your-bucket/reference-audio.mp3"
```

### 3. 准备漫画图像

将漫画图像文件放入 `input_images` 目录：

```bash
mkdir -p input_images
# 复制你的漫画图像到这个目录
```

支持的图像格式：`.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`

### 4. 运行处理流程

#### 完整流程（需要完整配置）
```bash
python3 run_comic_video.py --input input_images
```

#### 测试运行（仅分析图像）
```bash
python3 run_comic_video.py --input input_images --dry-run
```

#### 限制处理数量
```bash
python3 run_comic_video.py --input input_images --max-images 5
```

#### 详细输出
```bash
python3 run_comic_video.py --input input_images --verbose
```

## 📋 使用Jupyter Notebook

1. 打开 `comic_to_video_voice.ipynb`
2. 按顺序执行所有单元格
3. 在配置单元格中填入你的参数
4. 运行主流程

## 🔧 配置说明

### ComfyUI配置

1. **服务器地址**: 确保ComfyUI服务正在运行
2. **工作流文件**: 根据你的ComfyUI配置调整 `sample_workflow.json`

关键节点配置：
```json
{
  "image_input_node_id": {
    "inputs": {
      "image": ""  // 会被替换为base64图像
    }
  },
  "text_prompt_node_id": {
    "inputs": {
      "text": ""  // 会被替换为视频提示词
    }
  }
}
```

### GPT-SoVITS配置

1. **端点名称**: SageMaker端点名称
2. **参考音频**: 用于语音克隆的参考音频文件

### AWS配置

确保AWS凭证已正确配置：
```bash
aws configure
# 或设置环境变量
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2
```

## 📊 输出说明

### 目录结构
```
video_voice/
├── input_images/          # 输入漫画图像
├── output_videos/         # 生成的视频文件
├── output_audio/          # 生成的音频文件
├── final_videos/          # 合并后的视频
├── temp/                  # 临时文件
└── analysis_results_*.json # 图像分析结果
```

### 处理流程

1. **图像分析**: 使用Bedrock Nova分析漫画内容
2. **视频生成**: 通过ComfyUI生成动态视频
3. **语音合成**: 使用GPT-SoVITS生成配音
4. **视频合成**: 合并视频和音频
5. **最终输出**: 拼接完整视频

### 分析结果格式

```json
{
  "success": true,
  "file_path": "input_images/comic_01.jpg",
  "analysis_result": {
    "scene_description": "场景描述",
    "characters": "人物信息", 
    "dialogue_text": "对话文字",
    "story_content": "故事内容",
    "video_prompt": "视频生成提示词",
    "audio_script": "配音文本"
  }
}
```

## 🛠️ 故障排除

### 常见问题

1. **ffmpeg未找到**
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu
   sudo apt install ffmpeg
   ```

2. **Python包缺失**
   ```bash
   pip install boto3 requests pydub numpy
   ```

3. **ComfyUI连接失败**
   - 检查服务器URL和端口
   - 确认ComfyUI服务正在运行
   - 验证网络连接

4. **GPT-SoVITS调用失败**
   - 检查AWS凭证配置
   - 确认端点名称正确
   - 验证参考音频路径

### 调试模式

启用详细日志：
```bash
python3 run_comic_video.py --input input_images --verbose
```

测试单个功能：
```python
from comic_video_utils import ComicVideoProcessor

processor = ComicVideoProcessor()

# 测试图像分析
result = processor.analyze_comic_image_content("test_image.jpg")
print(result)

# 检查依赖
processor.check_dependencies()
```

## 📈 性能优化

### 批处理设置
```python
BATCH_SIZE = 3      # 每批处理图像数量
MAX_IMAGES = 10     # 最大处理图像数量
```

### 质量控制
```python
QUALITY_CONTROL = {
    "min_image_size": (512, 512),
    "max_image_size": (2048, 2048),
    "video_quality": "high",
    "audio_quality": "high"
}
```

### 内存管理
```python
PERFORMANCE = {
    "memory_limit_mb": 4096,
    "cleanup_temp_files": True
}
```

## 🎯 最佳实践

1. **小批量测试**: 先用少量图像测试流程
2. **质量检查**: 检查生成的视频和音频质量
3. **资源监控**: 注意内存和存储使用情况
4. **错误处理**: 启用错误继续处理模式
5. **备份结果**: 保存重要的中间结果

## 📞 获取帮助

如果遇到问题：

1. 查看详细日志输出
2. 检查配置文件设置
3. 验证系统依赖
4. 测试网络连接
5. 查看错误信息和堆栈跟踪

使用 `--help` 查看所有可用选项：
```bash
python3 run_comic_video.py --help
```
