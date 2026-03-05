#!/usr/bin/env python3
"""
测试代码同步报告器：测试_send_formatted_report方法在没有未同步项时的真实发送情况

此测试将**真实**向企业微信群聊发送消息，用于验证报告发送功能。
"""

import pytest
import json
import sys
import os
from datetime import datetime

# 添加父目录到sys.path以便导入app模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.code_sync_reporter import CodeSyncReporter
from app.webhook import webhook_sender
from app.config import WeChatConfig, MessageType


class TestFormattedReportNoUnsyncedRealSend:
    """测试_send_formatted_report方法在没有未同步项时的真实发送情况"""
    
    @pytest.fixture(scope="class")
    def reporter(self):
        """创建报告器实例"""
        return CodeSyncReporter()
    
    def test_send_formatted_report_no_unsynced_real_send(self, reporter):
        """
        测试_send_formatted_report方法，传入无未同步项的数据，进行真实消息发送
        
        此测试将：
        1. 构建一个模拟的JSON数据（无未同步项）
        2. 使用真实的webhook配置发送消息
        3. 验证消息发送成功
        """
        # 跳过测试条件：如果没有配置有效的WEBHOOK_URL
        if not WeChatConfig.WEBHOOK_URL:
            pytest.skip("WEBHOOK_URL未配置，跳过真实发送测试")
        
        # 准备测试数据：模拟完全同步的情况
        mock_json_data = {
            "check_time": datetime.now().isoformat(),
            "config": {
                "master_branch": "origin/master",
                "target_branch": "origin/v2.9.0-test"
            },
            "stats": {
                "master_count": 50,
                "target_count": 50,
                "unsynced_count": 0,  # 核心：没有未同步项
                "whitelisted_count": 3
            },
            "unsynced_commits": []  # 空列表，表示没有未同步commit
        }
        
        execution_log = f"测试执行日志\n测试时间: {datetime.now().isoformat()}\n测试类型: 无未同步项发送测试"
        
        # 使用真实的群组ID（从配置读取）
        real_group_id = str(WeChatConfig.GROUP_ID)
        
        print(f"\n{'='*60}")
        print("开始真实发送测试 - 无未同步项")
        print(f"目标群组ID: {real_group_id}")
        print(f"Webhook URL: {WeChatConfig.WEBHOOK_URL}")
        print(f"测试时间: {mock_json_data['check_time']}")
        print(f"{'='*60}")
        
        try:
            # 调用被测试的方法 - 这是真实调用，会实际发送消息
            result = reporter._send_formatted_report(
                real_group_id, 
                mock_json_data, 
                execution_log
            )
            
            # 打印详细结果
            print(f"\n发送结果:")
            print(f"  success: {result.get('success')}")
            print(f"  webhook_result: {json.dumps(result.get('webhook_result', {}), indent=2, ensure_ascii=False)}")
            print(f"  sync_data.keys: {list(result.get('sync_data', {}).keys())}")
            
            # 验证结果结构
            assert "success" in result, "结果中缺少success字段"
            assert "webhook_result" in result, "结果中缺少webhook_result字段"
            
            # 验证发送成功
            assert result.get("success") is True, f"消息发送失败: {result}"
            
            # 验证webhook结果
            webhook_result = result.get("webhook_result", {})
            assert webhook_result.get("success") is True, f"Webhook发送失败: {webhook_result}"
            
            # 验证同步数据
            sync_data = result.get("sync_data", {})
            assert sync_data.get("unsynced_commits") == [], "同步数据中不应该有未同步项"
            assert sync_data.get("stats", {}).get("unsynced_count") == 0, "未同步计数应该为0"
            
            print(f"\n✅ 测试通过：无未同步项的消息发送成功")
            print(f"   发送状态: {webhook_result.get('error_msg', '未知')}")
            print(f"   错误码: {webhook_result.get('errcode', '未知')}")
            
        except Exception as e:
            print(f"\n❌ 测试失败：{e}")
            # 记录详细错误信息
            import traceback
            traceback.print_exc()
            raise
    
    def test_message_content_format_no_unsynced(self, reporter):
        """
        验证无未同步项时消息内容格式
        
        此测试验证消息内容，但通过mock发送，不过度发送真实消息
        """
        # 准备测试数据
        mock_json_data = {
            "check_time": "2024-01-15T10:30:00",
            "config": {
                "master_branch": "origin/main",
                "target_branch": "origin/develop"
            },
            "stats": {
                "master_count": 100,
                "target_count": 98,
                "unsynced_count": 0,
                "whitelisted_count": 2
            },
            "unsynced_commits": []
        }
        
        execution_log = "格式化测试"
        
        # 使用mock来验证消息内容，而不实际发送
        from unittest.mock import Mock, patch
        with patch('app.code_sync_reporter.webhook_sender.send_multi_part_message') as mock_send:
            mock_result = {
                "success": True,
                "errcode": 0,
                "error_msg": "请求成功"
            }
            mock_send.return_value = mock_result
            
            test_group_id = "test_group_99999"
            
            # 调用方法
            result = reporter._send_formatted_report(
                test_group_id,
                mock_json_data,
                execution_log
            )
            
            # 验证发送被调用
            assert mock_send.called, "send_multi_part_message应该被调用"
            
            # 获取发送的参数
            call_args = mock_send.call_args
            assert call_args is not None
            
            sent_group_id = call_args[0][0]
            sent_messages = call_args[0][1]
            
            # 验证参数
            assert sent_group_id == test_group_id, f"发送的群组ID不匹配: {sent_group_id}"
            assert isinstance(sent_messages, list), "消息应该是一个列表"
            
            # 验证消息结构
            assert len(sent_messages) == 1, f"无未同步项时应该只有1条消息，实际有: {len(sent_messages)}"
            
            first_message = sent_messages[0]
            assert first_message.get("type") == MessageType.TEXT, "消息类型应该是TEXT"
            
            content = first_message.get("content", "")
            
            # 验证内容包含重要信息
            assert "代码同步检查报告" in content, "消息应该包含标题"
            assert "Master分支: origin/main" in content, "消息应该包含Master分支"
            assert "目标分支: origin/develop" in content, "消息应该包含目标分支"
            assert "Master commit数量: 100" in content, "消息应该包含Master数量"
            assert "目标分支 commit数量: 98" in content, "消息应该包含目标分支数量"
            assert "未同步 commit数量: 0" in content, "消息应该包含未同步数量"
            assert "✅ 本次同步检查未发现未同步commit" in content, "消息应该包含成功提示"
            
            # 验证没有AT消息
            at_messages = [m for m in sent_messages if m.get("type") == MessageType.AT]
            assert len(at_messages) == 0, "无未同步项时不应该有AT消息"
            
            print(f"\n✅ 消息格式验证通过")
            print(f"   消息长度: {len(content)}字符")
            print(f"   包含关键统计信息: 是")
    
    def test_edge_cases_no_unsynced(self, reporter):
        """
        测试边缘情况：最小化数据和异常情况
        """
        test_cases = [
            {
                "name": "最小数据",
                "data": {
                    "check_time": "2024-01-15T10:30:00",
                    "config": {},
                    "stats": {},
                    "unsynced_commits": []
                }
            },
            {
                "name": "零提交统计",
                "data": {
                    "check_time": "2024-01-15T10:30:00",
                    "config": {
                        "master_branch": "origin/master",
                        "target_branch": "origin/feature"
                    },
                    "stats": {
                        "master_count": 0,
                        "target_count": 0,
                        "unsynced_count": 0,
                        "whitelisted_count": 0
                    },
                    "unsynced_commits": []
                }
            },
            {
                "name": "大量提交但完全同步",
                "data": {
                    "check_time": "2024-01-15T10:30:00",
                    "config": {
                        "master_branch": "origin/master",
                        "target_branch": "origin/release"
                    },
                    "stats": {
                        "master_count": 1000,
                        "target_count": 1000,  # 完全相同
                        "unsynced_count": 0,
                        "whitelisted_count": 100
                    },
                    "unsynced_commits": []
                }
            }
        ]
        
        for test_case in test_cases:
            print(f"\n测试边缘情况: {test_case['name']}")
            
            execution_log = f"测试: {test_case['name']}"
            
            # 使用mock发送
            from unittest.mock import Mock, patch
            with patch('app.code_sync_reporter.webhook_sender.send_multi_part_message') as mock_send:
                mock_result = {
                    "success": True,
                    "errcode": 0,
                    "error_msg": "请求成功"
                }
                mock_send.return_value = mock_result
                
                test_group_id = "test_edge_case"
                
                # 调用方法
                result = reporter._send_formatted_report(
                    test_group_id,
                    test_case["data"],
                    execution_log
                )
                
                # 验证处理成功
                assert result.get("success") is True, f"测试用例 '{test_case['name']}' 失败"
                
                print(f"  ✅ {test_case['name']}: 处理成功")


def test_isolated_send_formatted_report():
    """单独测试_send_formatted_report方法"""
    reporter = CodeSyncReporter()
    
    # 准备测试数据
    test_data = {
        "check_time": "2024-01-15T14:30:00",
        "config": {
            "master_branch": "origin/master",
            "target_branch": "origin/test-branch"
        },
        "stats": {
            "master_count": 75,
            "target_count": 72,
            "unsynced_count": 0,
            "whitelisted_count": 3
        },
        "unsynced_commits": []
    }
    
    # 使用mock避免真实发送
    from unittest.mock import Mock, patch
    with patch('app.code_sync_reporter.webhook_sender.send_multi_part_message') as mock_send:
        mock_send.return_value = {"success": True, "errcode": 0}
        
        result = reporter._send_formatted_report(
            "test_isolated_group",
            test_data,
            "隔离测试日志"
        )
        
        assert result.get("success") is True
        assert mock_send.called
        
        # 验证消息内容
        call_args = mock_send.call_args
        if call_args:
            messages = call_args[0][1]
            assert len(messages) == 1
            assert messages[0]["type"] == MessageType.TEXT
            
            content = messages[0]["content"]
            assert "✅ 本次同步检查未发现未同步commit" in content
            assert "未同步 commit数量: 0" in content
        
        print("\n✅ 隔离测试通过")


if __name__ == "__main__":
    print("""
============================================================
📋 代码同步报告器测试 - 无未同步项的真实发送
============================================================

警告：此测试将实际向企业微信群聊发送消息！
请确保：
1. .env文件中配置了正确的WEBHOOK_URL和GROUP_ID
2. 您有权限向该群组发送消息
3. 测试期间可能会产生实际的群聊消息

测试将分为：
1. 真实发送测试（需要配置WEBHOOK_URL）
2. 消息格式验证（不实际发送）
3. 边缘情况测试（不实际发送）
""")
    
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))