#!/usr/bin/env python3
"""
简化版字幕测试脚本 - 使用指定字体文件
"""

import os
import sys
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


def add_simple_subtitle(video_path, output_path, subtitle_text, font='./yahei.ttf'):
    """
    使用指定字体文件添加字幕
    """
    print(f"📝 开始添加字幕...")
    print(f"📹 视频文件: {os.path.basename(video_path)}")
    print(f"💬 字幕内容: {subtitle_text}")
    print(f"🎨 字体文件: {font}")
    
    try:
        # 检查字体文件
        if not os.path.exists(font):
            print(f"❌ 字体文件不存在: {font}")
            return False
        
        # 加载视频
        video = VideoFileClip(video_path)
        print(f"📊 视频信息: {video.w}x{video.h}, 时长={video.duration:.2f}秒")
        
        # 创建字幕 (MoviePy 1.0.3 语法)
        txt_clip = TextClip(
            subtitle_text,  # 第一个参数直接是文本
            fontsize=10,    # 修改字体大小为10
            color='white',
            font=font
        )
        
        # 设置字幕位置和时长 (MoviePy 1.0.3 语法)
        txt_clip = txt_clip.set_position('bottom').set_duration(video.duration)
        
        # 合成视频
        final_video = CompositeVideoClip([video, txt_clip])
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 输出视频
        print(f"🎬 正在渲染视频...")
        final_video.write_videofile(output_path, verbose=False, logger=None)
        
        # 清理资源
        video.close()
        txt_clip.close()
        final_video.close()
        
        print(f"✅ 字幕视频已保存: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 添加字幕失败: {str(e)}")
        return False


def add_timed_captions(video_path, output_path, captions, font='./yahei.ttf'):
    """
    添加带时间轴的字幕（你提供的方法）
    
    Args:
        video_path: 视频文件路径
        output_path: 输出文件路径
        captions: 字幕列表，格式: [(text, start_time, end_time), ...]
        font: 字体文件路径
    """
    print(f"📝 开始添加带时间轴的字幕...")
    print(f"📹 视频文件: {os.path.basename(video_path)}")
    print(f"💬 字幕数量: {len(captions)}")
    print(f"🎨 字体文件: {font}")
    
    try:
        # 检查字体文件
        if not os.path.exists(font):
            print(f"❌ 字体文件不存在: {font}")
            return False
        
        # Load the video
        video = VideoFileClip(video_path)
        print(f"📊 视频信息: {video.w}x{video.h}, 时长={video.duration:.2f}秒")
        
        # Create text clips for each caption
        txt_clips = []
        
        for i, caption in enumerate(captions):
            text, start_time, end_time = caption
            print(f"  字幕 {i+1}: '{text}' ({start_time}s - {end_time}s)")
            
            txt_clip = TextClip(
                text,           # 第一个参数直接是文本
                fontsize=10,    # 修改字体大小为10
                color='white',
                font=font
            )
            txt_clip = txt_clip.set_position('bottom').set_start(start_time).set_end(end_time)
            txt_clips.append(txt_clip)
        
        # Combine video and all text clips
        final_video = CompositeVideoClip([video] + txt_clips)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write output video
        print(f"🎬 正在渲染视频...")
        final_video.write_videofile(output_path, verbose=False, logger=None)
        
        # Close clips
        video.close()
        final_video.close()
        
        print(f"✅ 带时间轴字幕视频已保存: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 添加字幕失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("🎬 简化版字幕测试脚本")
    print("=" * 50)
    
    # 查找测试视频
    video_path = None
    test_paths = ['./output_videos', './final_videos', '.']
    
    for path in test_paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith(('.mp4', '.avi', '.mov')):
                    video_path = os.path.join(path, file)
                    break
        if video_path:
            break
    
    if not video_path:
        print("❌ 未找到测试视频文件")
        return
    
    print(f"📹 使用测试视频: {video_path}")
    
    # 创建输出目录
    os.makedirs('output_video', exist_ok=True)
    
    # 测试1: 简单字幕（全程显示）
    print("\n🧪 测试1: 简单字幕（全程显示）")
    simple_output = 'output_video/simple_subtitle_test.mp4'
    subtitle_text = "这是使用雅黑字体的中文字幕测试"
    
    success1 = add_simple_subtitle(video_path, simple_output, subtitle_text)
    
    # 测试2: 带时间轴的字幕
    print("\n🧪 测试2: 带时间轴的字幕")
    timed_output = 'output_video/timed_subtitle_test.mp4'
    
    # 示例字幕时间轴
    captions = [
        ("第一段字幕：欢迎观看", 0, 2),
        ("第二段字幕：这是中文测试", 2, 4),
        ("第三段字幕：字幕效果很好", 4, 6)
    ]
    
    success2 = add_timed_captions(video_path, timed_output, captions)
    
    # 结果总结
    print("\n📊 测试结果总结")
    print("=" * 50)
    print(f"简单字幕测试: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"时间轴字幕测试: {'✅ 成功' if success2 else '❌ 失败'}")
    
    if success1 or success2:
        print(f"\n📁 输出文件位置: output_video/")
        print("🎬 请检查生成的视频文件确认字幕效果")
        
        # 显示输出文件
        if success1:
            print(f"  - {simple_output}")
        if success2:
            print(f"  - {timed_output}")
    else:
        print("\n❌ 所有测试都失败了")
        print("💡 请检查:")
        print("  1. yahei.ttf 字体文件是否存在")
        print("  2. MoviePy 是否正确安装")
        print("  3. 视频文件是否可读")


if __name__ == "__main__":
    main()
