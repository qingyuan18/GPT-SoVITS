# 漫画转视频配音系统使用指南

本系统实现了一个完整的流程：
1. 使用Bedrock Nova多模态模型提取漫画图像关键内容
2. 调用ComfyUI接口进行图生视频
3. 通过GPT-SoVITS接口生成语音
4. 合并视频和音频

## 🚀 快速开始

### 1. 检查系统依赖

#### 系统依赖

**FFmpeg** (视频处理)
```bash
# 安装ffmpeg (macOS)
brew install ffmpeg

# 安装ffmpeg (Ubuntu)
sudo apt update
sudo apt install ffmpeg

# 安装ffmpeg (Windows)
# 下载并安装 https://ffmpeg.org/download.html
```

**ImageMagick** (字幕文本渲染)
```bash
# 安装ImageMagick (macOS)
brew install imagemagick

# 安装ImageMagick (Ubuntu)
sudo apt update
sudo apt install imagemagick

# 安装ImageMagick (Windows)
# 下载并安装 https://imagemagick.org/script/download.php#windows
# 或使用 Chocolatey: choco install imagemagick
```

⚠️ **重要**: ImageMagick 是字幕功能的必需依赖。如果没有安装，添加字幕时会出现错误。

#### Python依赖
```bash
pip install boto3 requests pydub numpy moviepy
```

⚠️ **MoviePy 配置**: 如果 MoviePy 无法找到 ImageMagick，可能需要手动配置路径：
```python
# 在代码中添加（如果需要）
import os
os.environ['IMAGEIO_FFMPEG_EXE'] = '/usr/local/bin/ffmpeg'  # FFmpeg路径
# ImageMagick 通常会自动检测，如果有问题请检查安装
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
# Bedrock配置
BEDROCK_REGION = "us-west-2"
BEDROCK_MODEL_ID = "us.amazon.nova-pro-v1:0"

# ComfyUI配置
COMFYUI_SERVER_URL = "http://your-comfyui-server.com:8188"
COMFYUI_WORKFLOW_PATH = "sample_workflow.json"  # 或你的自定义工作流

# GPT-SoVITS配置
GPT_SOVITS_ENDPOINT = "your-gpt-sovits-endpoint-name"
REFERENCE_AUDIO_PATH = "s3://your-bucket/reference-audio.mp3"
REFERENCE_TEXT = "参考音频对应的文本内容"

# 批处理配置
BATCH_SIZE = 10  # 每批处理的图像数量
MAX_IMAGES = 80  # 最大处理图像数量
```

**注意**:
- 如果只想测试图像分析功能，可以只配置Bedrock相关参数
- 完整的视频生成需要配置所有参数

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

#### 仅图像分析（无需ComfyUI和GPT-SoVITS配置）
```bash
python3 run_comic_video.py --input input_images
# 系统会自动检测配置，如果缺少完整配置则只执行图像分析
```

#### 测试运行（仅分析图像，显示详细结果）
```bash
python3 run_comic_video.py --input input_images --dry-run
```

#### 限制处理数量
```bash
python3 run_comic_video.py --input input_images --max-images 5
```

#### 自定义输出文件名
```bash
python3 run_comic_video.py --input input_images --output my_comic_video.mp4
```

#### 详细输出
```bash
python3 run_comic_video.py --input input_images --verbose
```

#### 处理完成后清理临时文件
```bash
python3 run_comic_video.py --input input_images --cleanup
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

#### 完整流程（5个步骤）
1. **图像分析**: 使用Bedrock Nova批量分析漫画内容，每批次选择最佳图像
2. **视频生成**: 通过ComfyUI从选中图像生成动态视频
3. **语音合成**: 使用GPT-SoVITS根据分析结果生成配音
4. **视频合成**: 合并视频和音频文件
5. **最终输出**: 拼接所有视频片段为完整视频

#### 仅分析模式（1个步骤）
1. **图像分析**: 使用Bedrock Nova批量分析漫画内容，输出JSON格式的分析结果

#### 新的批量处理特性
- **多图像分析**: 每批次同时分析多张图像，提供整体故事理解
- **智能选择**: 自动选择最适合视频生成的图像
- **简化输出**: 使用扁平化的JSON结构，便于后续处理

### 分析结果格式

#### 新的简化格式（与notebook一致）
```json
{
  "success": true,
  "file_path": "input_images/selected_comic.jpg",
  "analysis_result": {
    "overall_analysis": {
      "story_flow": "整体故事流程和连贯性分析",
      "main_theme": "主要主题和情节发展",
      "character_development": "人物发展和关系变化"
    },
    "selected_index": 2,
    "video_prompt": "基于整个批次图像的完整视频生成提示词",
    "combined_audio_script": "结合整个批次所有图像信息生成的完整配音文本"
  },
  "is_selected_from_batch": true,
  "batch_image_paths": ["image1.jpg", "image2.jpg", "image3.jpg"],
  "batch_analysis": "完整的批次分析结果"
}
```

#### 输出文件
- `analysis_results_YYYYMMDD_HHMMSS.json`: 完整的分析结果
- `temp/selected_images_info.json`: 每批次选中的图像信息
- `comic_video_YYYYMMDD_HHMMSS.mp4`: 最终生成的视频（完整流程）

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
   pip install boto3 requests pydub numpy moviepy
   ```

3. **ImageMagick未安装或配置错误**

   **错误信息**: `MoviePy Error: creation of None failed because of the following error: [Errno 2] No such file or directory: 'unset'`

   **解决方案**:
   ```bash
   # macOS
   brew install imagemagick

   # Ubuntu
   sudo apt install imagemagick

   # Windows
   # 下载安装 https://imagemagick.org/script/download.php#windows
   ```

   **验证安装**:
   ```bash
   # 检查 ImageMagick 是否正确安装
   convert -version
   # 或
   magick -version
   ```

4. **字幕添加失败**

   **错误信息**: `index -57665 is out of bounds for axis 0 with size 42336`

   **解决方案**:
   - 检查 `temp/temp_merged_*.mp4` 文件是否正常
   - 尝试使用修复版本的字幕函数
   - 考虑移除强制编码参数，让 MoviePy 保持原有格式

5. **ComfyUI连接失败**
   - 检查服务器URL和端口
   - 确认ComfyUI服务正在运行
   - 验证网络连接

6. **GPT-SoVITS调用失败**
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

# 创建处理器（可以传入配置参数）
processor = ComicVideoProcessor(
    bedrock_region="us-west-2",
    bedrock_model_id="us.amazon.nova-pro-v1:0",
    batch_size=3,
    max_images=10
)

# 测试批量图像分析
results = processor.batch_analyze_comic_images("input_images", max_files=5)
for result in results:
    if result['success']:
        print(f"选中图像: {result['file_path']}")
        print(f"主题: {result['analysis_result']['overall_analysis']['main_theme']}")

# 测试单张图像分析（兼容模式）
result = processor.analyze_comic_image_content("test_image.jpg")
print(result)

# 检查依赖
processor.check_dependencies()

# 测试完整流程（需要完整配置）
if processor.comfyui_server_url and processor.gpt_sovits_endpoint:
    final_video = processor.process_comic_to_video_voice("input_images")
    print(f"最终视频: {final_video}")
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
