#!/usr/bin/env python3
"""
漫画转视频配音命令行工具

使用方法:
python run_comic_video.py --input input_images --config config.py
"""

import argparse
import sys
import os
import importlib.util
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comic_video_utils import ComicVideoProcessor

def load_config(config_path):
    """
    动态加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置模块
    """
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return None
    
    spec = importlib.util.spec_from_file_location("config", config_path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    
    return config

def main():
    parser = argparse.ArgumentParser(
        description="漫画图像转视频配音工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run_comic_video.py --input input_images
  python run_comic_video.py --input /path/to/comics --config my_config.py
  python run_comic_video.py --input comics --output final_video.mp4 --max-images 5
  python run_comic_video.py --check-deps  # 仅检查依赖
  python run_comic_video.py --input comics --cleanup  # 处理后清理临时文件（保留调试文件）
  python run_comic_video.py --input comics --cleanup-all  # 处理后清理所有临时文件
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="input_images",
        help="输入漫画图像目录 (默认: input_images)"
    )
    
    parser.add_argument(
        "--output", "-o", 
        type=str,
        help="输出视频文件名 (默认: 自动生成时间戳文件名)"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.py",
        help="配置文件路径 (默认: config.py)"
    )
    
    parser.add_argument(
        "--max-images",
        type=int,
        help="最大处理图像数量 (覆盖配置文件设置)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        help="批处理大小 (覆盖配置文件设置)"
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="仅检查系统依赖，不执行处理"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true", 
        help="测试运行，不实际生成视频和音频"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="启用详细输出"
    )
    
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="处理完成后清理临时文件（保留temp_merged文件用于调试）"
    )

    parser.add_argument(
        "--cleanup-all",
        action="store_true",
        help="处理完成后清理所有临时文件（包括temp_merged文件）"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    print("🎬 漫画转视频配音工具")
    print("=" * 50)
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        # 使用默认配置
        print("⚠️ 使用默认配置")
        processor = ComicVideoProcessor()
    else:
        # 验证配置
        if hasattr(config, 'validate_config'):
            if not config.validate_config():
                print("❌ 配置验证失败，退出")
                return 1
        
        # 创建处理器
        processor = ComicVideoProcessor(
            bedrock_region=getattr(config, 'BEDROCK_REGION', 'us-west-2'),
            bedrock_model_id=getattr(config, 'BEDROCK_MODEL_ID', 'us.amazon.nova-lite-v1:0'),
            comfyui_server_url=getattr(config, 'COMFYUI_SERVER_URL', ''),
            comfyui_workflow_path=getattr(config, 'COMFYUI_WORKFLOW_PATH', ''),
            gpt_sovits_endpoint=getattr(config, 'GPT_SOVITS_ENDPOINT', ''),
            reference_audio_path=getattr(config, 'REFERENCE_AUDIO_PATH', ''),
            batch_size=args.batch_size or getattr(config, 'BATCH_SIZE', 3),
            max_images=args.max_images or getattr(config, 'MAX_IMAGES', 10)
        )
    
    # 仅检查依赖
    if args.check_deps:
        print("\n🔧 检查系统依赖...")
        if processor.check_dependencies():
            print("✅ 所有依赖检查通过")
            return 0
        else:
            print("❌ 依赖检查失败")
            return 1
    
    # 检查输入目录
    if not os.path.exists(args.input):
        print(f"❌ 输入目录不存在: {args.input}")
        return 1
    
    # 获取图像文件
    images = processor.get_comic_images_from_directory(args.input)
    if not images:
        print(f"❌ 输入目录中没有图像文件: {args.input}")
        return 1
    
    print(f"📊 找到 {len(images)} 个图像文件")
    
    # 检查依赖
    print("\n🔧 检查系统依赖...")
    if not processor.check_dependencies():
        print("❌ 系统依赖检查失败，请安装缺失的依赖")
        return 1
    
    # 测试运行
    if args.dry_run:
        print("\n🧪 测试运行模式")
        print("将执行以下步骤:")
        print("1. 分析漫画图像内容")
        print("2. 生成视频 (跳过)")
        print("3. 生成语音 (跳过)")
        print("4. 合并视频和音频 (跳过)")
        print("5. 拼接最终视频 (跳过)")
        
        # 只执行图像分析（使用多图像API）
        print(f"\n📊 分析 {len(images)} 个图像（多图像模式）...")

        # 使用新的批量分析方法
        analysis_results = processor.batch_analyze_comic_images(args.input, processor.max_images)

        print(f"\n📊 测试运行结果:")
        for i, result in enumerate(analysis_results, 1):
            if result.get('success'):
                selected_path = result.get('file_path', '')
                analysis = result.get('analysis_result', {})

                print(f"  批次 {i}:")
                print(f"    🔑 选中图像: {os.path.basename(selected_path)}")

                if 'overall_analysis' in analysis:
                    main_theme = analysis['overall_analysis'].get('main_theme', '')
                    print(f"    🎭 主要主题: {main_theme[:80]}...")

                if 'video_prompt' in analysis:
                    video_prompt = analysis['video_prompt']
                    print(f"    🎬 视频提示: {video_prompt[:80]}...")

                if 'combined_audio_script' in analysis:
                    audio_script = analysis['combined_audio_script']
                    print(f"    🎙️ 配音文本: {audio_script[:80]}...")
            else:
                print(f"  批次 {i}: ❌ 分析失败 - {result.get('error', '')}")

        print("\n✅ 测试运行完成")
        return 0
    
    # 执行完整流程
    print(f"\n🚀 开始处理 {args.input}")

    try:
        # 检查是否配置了完整的服务
        has_comfyui = bool(processor.comfyui_server_url and processor.comfyui_workflow_path)
        has_gpt_sovits = bool(processor.gpt_sovits_endpoint and processor.reference_audio_path)

        if has_comfyui and has_gpt_sovits:
            # 执行完整流程
            print("\n🎬 执行完整的漫画转视频配音流程")
            final_video = processor.process_comic_to_video_voice(args.input)

            if final_video:
                print(f"\n🎉 完整流程成功完成！")
                print(f"📁 最终视频: {final_video}")

                if args.output:
                    # 如果指定了输出文件名，重命名最终视频
                    import shutil
                    try:
                        shutil.move(final_video, args.output)
                        print(f"📁 视频已重命名为: {args.output}")
                    except Exception as e:
                        print(f"⚠️ 重命名失败: {e}")

                # 清理临时文件
                if args.cleanup_all:
                    print("\n🧹 清理所有临时文件...")
                    processor.cleanup_all_temp_files()
                elif args.cleanup:
                    print("\n🧹 清理临时文件（保留调试文件）...")
                    processor.cleanup_temp_files()

                return 0
            else:
                print("❌ 完整流程执行失败")
                return 1
        else:
            # 只执行图像分析部分
            print("\n📊 执行图像分析流程（缺少完整配置）")
            if not has_comfyui:
                print("⚠️ 缺少ComfyUI配置，跳过视频生成")
            if not has_gpt_sovits:
                print("⚠️ 缺少GPT-SoVITS配置，跳过语音生成")

            # 使用新的批量分析方法
            analysis_results = processor.batch_analyze_comic_images(args.input, processor.max_images)

            successful_results = [r for r in analysis_results if r.get('success')]
            print(f"\n✅ 成功分析 {len(successful_results)} 个批次")

            if not successful_results:
                print("❌ 没有成功分析的批次，退出")
                return 1

            # 保存分析结果
            import json
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"analysis_results_{timestamp}.json"

            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, ensure_ascii=False, indent=2)

            print(f"📄 分析结果已保存: {results_file}")

            # 显示统计信息
            print(f"\n📊 处理统计:")
            print(f"  • 输入图像: {len(images)}")
            print(f"  • 处理图像: {min(len(images), processor.max_images)}")
            print(f"  • 成功分析: {len(successful_results)}")
            print(f"  • 失败分析: {len(analysis_results) - len(successful_results)}")

            print("\n✅ 图像分析完成!")
            print("⚠️ 注意: 完整的视频生成功能需要配置ComfyUI和GPT-SoVITS")

            # 清理临时文件
            if args.cleanup_all:
                print("\n🧹 清理所有临时文件...")
                processor.cleanup_all_temp_files()
            elif args.cleanup:
                print("\n🧹 清理临时文件（保留调试文件）...")
                processor.cleanup_temp_files()

            return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断处理")
        return 1
    except Exception as e:
        print(f"\n❌ 处理过程中发生错误: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
