#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сброс статуса видео в реестре для повторной обработки
"""

import sys
import os

# Add current directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.video_registry import VideoRegistry

def reset_status(video_id):
    registry = VideoRegistry()
    if registry.video_exists(video_id):
        print(f"Сброс статуса для видео {video_id}...")
        registry.update_status(video_id, "pending")
        print("✅ Статус сброшен на 'pending'")
    else:
        print(f"❌ Видео {video_id} не найдено в реестре")

if __name__ == "__main__":
    reset_status("izzQ_oPSPAc")