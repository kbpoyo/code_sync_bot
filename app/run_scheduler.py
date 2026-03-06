#!/usr/bin/env python3
"""
容器环境定时任务调度器
在没有cron的容器环境中，使用Python的APScheduler实现定时任务
"""

import sys
import os
import time
import signal
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import ScheduleConfig, SchedulerLogConfig
from .code_sync_reporter import CodeSyncReporter

# 使用独立的定时任务日志配置
logger = SchedulerLogConfig.setup_logging()


class SimpleScheduler:
    """简单的定时任务调度器"""
    
    def __init__(self):
        self.scheduler = None
        self.reporter = CodeSyncReporter()
        self.running = False
        
    def start(self):
        """启动调度器"""
        if not ScheduleConfig.ENABLED:
            logger.info("定时任务未启用，退出调度器")
            return False
        
        # 验证配置
        if not ScheduleConfig.validate_sync_time():
            logger.error(f"定时任务时间格式错误: {ScheduleConfig.SYNC_TIME}")
            return False
        
        try:
            # 创建后台调度器
            self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
            
            # 解析时间
            hour, minute = ScheduleConfig.SYNC_TIME.split(':')
            
            # 添加定时任务
            self.scheduler.add_job(
                self.sync_check_job,
                trigger=CronTrigger(hour=int(hour), minute=int(minute)),
                id='daily_code_sync',
                name='每日代码同步检查',
                replace_existing=True,
                misfire_grace_time=3600  # 错过执行后1小时内仍可执行
            )
            
            # 启动调度器
            self.scheduler.start()
            self.running = True
            
            logger.info("=" * 60)
            logger.info("定时任务调度器已启动")
            logger.info(f"执行时间: 每天 {ScheduleConfig.SYNC_TIME}")
            logger.info(f"目标群组: {ScheduleConfig.SYNC_GROUP_ID}")
            logger.info("=" * 60)
            
            # 打印下一次执行时间
            job = self.scheduler.get_job('daily_code_sync')
            if job:
                logger.info(f"下一次执行: {job.next_run_time}")
            
            return True
            
        except Exception as e:
            logger.error(f"启动调度器失败: {e}", exc_info=True)
            return False
    
    def sync_check_job(self):
        """执行同步检查任务"""
        try:
            logger.info("=" * 60)
            logger.info("开始执行定时代码同步检查任务")
            logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"目标群组: {ScheduleConfig.SYNC_GROUP_ID}")
            logger.info("=" * 60)
            
            # 执行同步检查
            result = self.reporter.run_code_sync(ScheduleConfig.SYNC_GROUP_ID)
            
            if result.get("success"):
                logger.info("✅ 代码同步检查执行成功")
            else:
                logger.error(f"❌ 代码同步检查执行失败: {result.get('execution_log', '未知错误')}")
                
        except Exception as e:
            logger.error(f"定时任务执行异常: {e}", exc_info=True)
    
    def trigger_now(self):
        """手动触发一次同步检查"""
        logger.info("手动触发同步检查")
        self.sync_check_job()
    
    def stop(self):
        """停止调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self.running = False
            logger.info("调度器已停止")
    
    def run_forever(self):
        """持续运行调度器"""
        if not self.running:
            logger.error("调度器未启动")
            return
        
        logger.info("调度器运行中，按 Ctrl+C 停止...")
        
        try:
            # 主循环
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n收到停止信号...")
            self.stop()
        except Exception as e:
            logger.error(f"调度器运行异常: {e}", exc_info=True)
            self.stop()


def main():
    """主函数"""
    logger.info("启动定时任务调度器...")
    
    # 创建调度器
    scheduler = SimpleScheduler()
    
    # 启动调度器
    if not scheduler.start():
        logger.error("调度器启动失败，退出")
        sys.exit(1)
    
    # 注册信号处理器
    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，停止调度器...")
        scheduler.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 持续运行
    scheduler.run_forever()
    
    logger.info("调度器已退出")
    sys.exit(0)


if __name__ == "__main__":
    main()