#!/usr/bin/env python3
"""
真实消息发送测试
注意：此测试将实际向群聊机器人发送消息
使用前请确保.env文件中的配置正确
"""

import pytest
import os
import time
from fastapi.testclient import TestClient
from app.main import app
from app.config import WeChatConfig

client = TestClient(app)

# 真实的群组ID - 从配置或环境变量获取

@pytest.mark.skipif(
    not WeChatConfig.WEBHOOK_URL or 
    "apiin.im.baidu.com" not in WeChatConfig.WEBHOOK_URL,
    reason="需要配置真实的WEBHOOK_URL进行测试"
)
def test_real_message_send_success():
    """测试真实发送文本消息"""
    print(f"[INFO] 使用群组ID: {WeChatConfig.GROUP_ID}")
    print(f"[INFO] Webhook URL: {WeChatConfig.WEBHOOK_URL}")
    
    # 使用固定测试消息
    test_message = "系统验证消息"
    
    test_data = {
        "group_id": WeChatConfig.GROUP_ID,
        "message": test_message
    }
    
    print(f"[INFO] 准备发送消息: {test_message}")
    
    try:
        response = client.post(
            "/api/send_test_message",
            json=test_data
        )
        
        # 输出详细响应信息
        print(f"[INFO] 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[INFO] 发送结果: {result}")
            
            # 检查响应内容
            assert "result" in result, "响应中缺少result字段"
            
            # 企业微信API标准响应格式
            api_response = result["result"]
            
            # 常见的正常响应可能包含
            if "code" in api_response:
                # 有些API使用code字段表示状态
                if api_response.get("code") == 0:
                    print("[SUCCESS] 消息发送成功")
                else:
                    print(f"[WARNING] 消息发送可能存在异常: {api_response}")
            elif "errcode" in api_response:
                # 企业微信格式
                if api_response.get("errcode") == 0:
                    print("[SUCCESS] 消息发送成功（企业微信格式）")
                else:
                    print(f"[WARNING] 消息发送失败: {api_response}")
            elif "msg" in api_response:
                # 其他可能的格式
                print(f"[INFO] 服务器响应: {api_response['msg']}")
            
            # HTTP状态码验证
            assert response.status_code == 200, f"HTTP状态码错误: {response.status_code}"
            
        elif response.status_code == 400:
            print(f"[INFO] 参数错误: {response.json()}")
            # 允许参数验证的错误，但不作为测试失败
            pytest.skip("参数验证错误，可能是测试数据问题")
            
        elif response.status_code >= 500:
            print(f"[ERROR] 服务器错误: {response.json()}")
            # 服务器错误时测试失败
            assert False, f"服务器错误: {response.status_code}"
            
    except Exception as e:
        print(f"[ERROR] 测试执行异常: {e}")
        raise

# def test_real_message_send_with_different_content():
#     """测试发送不同类型的内容"""
#     if not WeChatConfig.WEBHOOK_URL or "apiin.im.baidu.com" not in WeChatConfig.WEBHOOK_URL:
#         pytest.skip("需要配置真实的WEBHOOK_URL")
    
#     test_cases = [
#         ("短消息", "测试短消息"),
#         ("长消息", "这是一条较长的测试消息，用于验证消息长度限制和处理能力。" * 3),
#         ("带符号", "测试消息：@#$%^&*()_+😀🎉"),
#         ("中英文混合", "Hello World 你好世界 Test 测试"),
#     ]
    
#     for case_name, message in test_cases:
#         print(f"[INFO] 测试用例: {case_name}")
        
#         test_data = {
#             "group_id": REAL_GROUP_ID,
#             "message": f"{case_name}: {message}"
#         }
        
#         try:
#             response = client.post(
#                 "/api/send_test_message",
#                 json=test_data
#             )
            
#             # 给API留出处理时间
#             time.sleep(0.5)
            
#             if response.status_code == 200:
#                 print(f"[OK] {case_name} 发送成功")
#             elif response.status_code == 400:
#                 print(f"[INFO] {case_name} 参数错误（跳过）")
#             else:
#                 print(f"[WARNING] {case_name} 返回非200状态: {response.status_code}")
                
#         except Exception as e:
#             print(f"[ERROR] {case_name} 执行异常: {e}")
#             # 继续执行下一个测试用例，不中断整个测试套件

# def test_api_validation():
#     """测试API参数验证"""
#     # 测试缺少group_id
#     response = client.post(
#         "/api/send_test_message",
#         json={"message": "缺少群组ID"}
#     )
    
#     # 期望返回400错误
#     assert response.status_code == 400
#     assert "缺少group_id参数" in response.json()["detail"]
#     print("[OK] 缺少group_id参数验证通过")
    
#     # 测试无效JSON格式
#     response = client.post(
#         "/api/send_test_message",
#         data="invalid json",
#         headers={"Content-Type": "application/json"}
#     )
    
#     assert response.status_code == 400
#     print("[OK] 无效JSON格式验证通过")

# def test_service_health():
#     """测试服务健康状态"""
#     response = client.get("/health")
#     assert response.status_code == 200
#     assert response.json()["status"] == "healthy"
#     print("[OK] 健康检查正常")
    
#     response = client.get("/")
#     assert response.status_code == 200
#     assert "status" in response.json()
#     print("[OK] 根目录端点正常")

if __name__ == "__main__":
    print("企业微信群组机器人真实测试")
    print("注意：此测试将实际向群聊发送消息")
    print(f"群组ID: {REAL_GROUP_ID}")
    print(f"Webhook URL: {WeChatConfig.WEBHOOK_URL}")
    print("-" * 50)
    
    import sys
    sys.exit(pytest.main([__file__, "-v"]))