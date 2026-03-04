import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.config import WeChatConfig

client = TestClient(app)

@pytest.fixture
def mock_webhook():
    with patch("app.webhook.webhook_sender") as mock:
        yield mock

def test_send_text_message_success(mock_webhook):
    """测试成功发送文本消息（mock版本）"""
    # 配置模拟返回值
    mock_response = {"errcode": 0, "errmsg": "ok"}
    mock_webhook.send_text_message.return_value = mock_response
    
    # 使用测试群组ID
    test_data = {
        "group_id": "test_group_123",
        "message": "这是一条测试消息"
    }
    
    # 调用API
    response = client.post(
        "/api/send_test_message",
        json=test_data
    )
    
    # 验证
    assert response.status_code == 200
    assert response.json()["result"] == mock_response
    mock_webhook.send_text_message.assert_called_once_with(
        group_id="test_group_123",  # 保持一致
        content="这是一条测试消息",
        at_users=[]
    )

def test_send_message_missing_group_id(mock_webhook):
    """测试缺少group_id参数"""
    response = client.post(
        "/api/send_test_message",
        json={"message": "无效请求"}
    )
    
    assert response.status_code == 400
    assert "缺少group_id参数" in response.json()["detail"]

def test_send_message_empty_content(mock_webhook):
    """测试空消息内容"""
    mock_response = {"errcode": 0, "errmsg": "ok"}
    mock_webhook.send_text_message.return_value = mock_response
    
    response = client.post(
        "/api/send_test_message",
        json={"group_id": "test_group_123", "message": ""}
    )
    
    assert response.status_code == 200
    mock_webhook.send_text_message.assert_called_once_with(
        group_id="test_group_123",
        content="",
        at_users=[]
    )

def test_send_message_api_failure(mock_webhook):
    """测试API调用失败情况"""
    mock_webhook.send_text_message.side_effect = Exception("API调用失败")
    
    response = client.post(
        "/api/send_test_message",
        json={"group_id": "test_group_123", "message": "失败测试"}
    )
    
    assert response.status_code == 500
    assert "发送消息失败" in response.json()["detail"]

def test_send_message_with_mentions(mock_webhook):
    """测试发送带@提醒的消息"""
    mock_response = {"errcode": 0, "errmsg": "ok"}
    mock_webhook.send_text_message.return_value = mock_response
    
    response = client.post(
        "/api/send_test_message",
        json={
            "group_id": "test_group_123",
            "message": "测试@提醒",
            "at_users": ["user1", "user2"]
        }
    )
    
    assert response.status_code == 200
    mock_webhook.send_text_message.assert_called_once_with(
        group_id="test_group_123",
        content="测试@提醒",
        at_users=["user1", "user2"]
    )