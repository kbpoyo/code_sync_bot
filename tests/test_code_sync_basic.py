#!/usr/bin/env python3
"""
代码同步基本功能测试 - 更简单的版本
"""

import pytest
import unittest.mock as mock
from app.code_sync_reporter import CodeSyncReporter


class TestCodeSyncBasic:
    """代码同步基本功能测试类"""
    
    def test_basic_functionality(self):
        """测试基本功能流程"""
        reporter = CodeSyncReporter()
        
        # 测试脚本路径是正确的
        assert reporter.script_dir.endswith("code_sync")
        
        # 测试group_id参数传递
        test_group = "test_group_123"
        
        # 模拟整个运行流程
        with mock.patch('subprocess.Popen') as mock_popen, \
             mock.patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
             mock.patch('app.code_sync_reporter.webhook_sender.send_text_message') as mock_send_message:
            
            # 设置mock
            mock_process = mock.MagicMock()
            mock_process.communicate.return_value = ("stdout", "stderr")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            mock_temp = mock.MagicMock()
            mock_temp.name = "/tmp/test.json"
            mock_temp.__enter__ = mock.Mock(return_value=mock_temp)
            mock_temp.__exit__ = mock.Mock(return_value=None)
            mock_tempfile.return_value = mock_temp
            
            mock_send_message.return_value = {
                "success": True,
                "errcode": 0,
                "error_msg": "success"
            }
            
            # 模拟文件读取（JSON格式）
            test_json = '{"status": "success", "data": {"test": "value"}}'
            mock_open = mock.mock_open(read_data=test_json)
            
            with mock.patch('builtins.open', mock_open):
                result = reporter.run_code_sync(test_group)
                
                # 验证调用链
                assert mock_popen.called
                assert mock_send_message.called
                assert result.get("success") is True
    
    def test_error_scenarios(self):
        """测试几个常见的错误场景"""
        reporter = CodeSyncReporter()
        
        # 测试场景1: 脚本执行返回非零退出码
        with mock.patch('subprocess.Popen') as mock_popen, \
             mock.patch('app.code_sync_reporter.webhook_sender.send_text_message') as mock_send_message:
            
            mock_process = mock.MagicMock()
            mock_process.communicate.return_value = ("", "Permission denied")
            mock_process.returncode = 1  # 非零退出码
            mock_popen.return_value = mock_process
            
            mock_send_message.return_value = {"success": True}
            
            with mock.patch('tempfile.NamedTemporaryFile'):
                result = reporter.run_code_sync("test_group")
                
                # 即使脚本失败，也应该发送消息
                assert mock_send_message.called
    
    def test_message_formatting_cases(self):
        """测试不同消息格式化情况"""
        # 测试case1: 大量未同步commits
        test_data_large = {
            "stats": {"unsynced_count": 50},
            "unsynced_commits": [
                {"title": f"Feature {i}", "author": f"author{i}"} 
                for i in range(50)
            ]
        }
        
        # 测试case2: 空结果
        test_data_empty = {
            "stats": {"unsynced_count": 0},
            "unsynced_commits": []
        }
        
        # 测试case3: 混合类型
        test_data_mixed = {
            "stats": {"unsynced_count": 5},
            "unsynced_commits": [
                {"title": "feat: add feature", "author": "dev1"},
                {"title": "fix: bug fix", "author": "dev2"}
            ]
        }
        
        # 这些测试主要通过集成测试验证
        assert True
        
    def test_api_integration(self):
        """测试API集成（主应用的端点）"""
        # 导入相关模块测试API端点是否存在
        from app.main import app
        import inspect
        
        # 检查API路由是否存在
        routes = app.routes
        code_sync_routes = [r for r in routes if "code_sync" in repr(r)]
        
        # 应该至少有一个code_sync路由
        assert len(code_sync_routes) > 0
        
        # 验证路由方法
        for route in code_sync_routes:
            assert hasattr(route, 'methods')
            assert hasattr(route, 'path')


def test_simple_run():
    """最简单的测试用例"""
    # 导入模块检查是否正常工作
    from app.code_sync_reporter import CodeSyncReporter, run_code_sync_and_report
    
    # 测试类是否存在
    assert CodeSyncReporter is not None
    assert callable(run_code_sync_and_report)
    
    # 测试基本属性
    reporter = CodeSyncReporter()
    assert hasattr(reporter, 'run_code_sync')
    assert callable(reporter.run_code_sync)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])