#!/usr/bin/env python3
"""
代码同步集成测试 - 实际执行测试
"""

import pytest
import os
import subprocess
import json
from pathlib import Path
from app.code_sync_reporter import CodeSyncReporter

class TestCodeSyncIntegration:
    """代码同步集成测试类"""
    
    @classmethod
    def setup_class(cls):
        """类级别设置"""
        cls.reporter = CodeSyncReporter()
        cls.test_group = "12566106"  # 使用测试群组ID
        cls.script_dir = Path(__file__).parent.parent / "code_sync"
        
        # 确保测试环境存在
        if not cls.script_dir.exists():
            pytest.skip("code_sync目录不存在")
    
    def test_script_execution(self):
        """测试脚本可以正常执行"""
        script_path = self.script_dir / "code_sync.sh"
        assert script_path.exists(), "code_sync.sh脚本不存在"
        
        # 临时修改环境变量，使用测试配置
        env = os.environ.copy()
        env["REPO_DIR"] = str(self.script_dir / "XMLIR")
        env["OUTPUT_FORMAT"] = "json"
        
        # 执行脚本
        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                cwd=str(self.script_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=60  # 1分钟超时
            )
            
            # 验证执行结果
            assert result.returncode == 0, f"脚本执行失败: {result.stderr}"
            print("脚本执行成功")
                
        except subprocess.TimeoutExpired:
            pytest.fail("脚本执行超时")
        except Exception as e:
            pytest.fail(f"执行脚本时出错: {str(e)}")
    
    def test_reporter_with_real_script(self):
        """测试报告器与真实脚本集成"""
        # 执行报告器
        result = self.reporter.run_code_sync(self.test_group)
        
        # 验证结果结构
        assert isinstance(result, dict), "结果不是字典类型"
        assert "success" in result, "结果缺少success字段"
        
        # 如果成功，验证返回的数据
        if result["success"]:
            assert "webhook_result" in result, "缺少webhook_result"
            assert "sync_data" in result, "缺少sync_data"
        else:
            assert "error" in result, "失败时缺少error信息"
    
    def test_output_formats(self):
        """测试不同输出格式"""
        formats = ["json", "text"]
        
        for fmt in formats:
            # 设置环境变量
            env = os.environ.copy()
            env["REPO_DIR"] = str(self.script_dir / "XMLIR")
            env["OUTPUT_FORMAT"] = "json"
            
            # 执行脚本
            script_path = self.script_dir / "code_sync.sh"
            result = subprocess.run(
                ["bash", str(script_path)],
                cwd=str(self.script_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            assert result.returncode == 0, f"{fmt}格式执行失败: {result.stderr}"
            
            # 验证输出
            if fmt == "json":
                try:
                    json.loads(result.stdout)
                except json.JSONDecodeError:
                    pytest.fail("JSON格式输出无效")
            else:
                assert result.stdout, "文本输出为空"
    
    def test_error_conditions(self):
        """测试错误条件"""
        # 测试无效的仓库路径
        env = os.environ.copy()
        env["REPO_DIR"] = str(self.script_dir / "nonexistent_repo")
        
        script_path = self.script_dir / "code_sync.sh"
        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=str(self.script_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        assert result.returncode != 0, "无效仓库路径应该导致失败"
        assert "ERROR" in result.stderr, "错误情况应该输出ERROR"
    
    # def test_required_environment_variables(self):
    #     """测试必需的环境变量"""
    #     required_vars = ["REPO_URL", "MASTER_SYNC_BASE", "TARGET_SYNC_BASE"]
        
    #     for var in required_vars:
    #         # 临时移除环境变量
    #         env = os.environ.copy()
    #         env.pop(var, None)
            
    #         script_path = self.script_dir / "code_sync.sh"
    #         result = subprocess.run(
    #             ["bash", str(script_path)],
    #             cwd=str(self.script_dir),
    #             env=env,
    #             capture_output=True,
    #             text=True,
    #             timeout=60
    #         )
            
    #         assert result.returncode != 0, f"缺少{var}应该导致失败"
    #         assert var in result.stderr, f"错误信息应该提到{var}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])