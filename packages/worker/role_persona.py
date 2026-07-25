"""角色换装 — 每个 sub-agent 有自己的角色、头像、system prompt。"""

from __future__ import annotations

ROLES = {
    "pm": {
        "name": "项目经理",
        "avatar": "/avatars/pm.png",
        "system": "你是项目经理，负责拆解任务、协调进度、确保交付质量。回复简洁，关注关键路径。",
    },
    "designer": {
        "name": "UI 设计师",
        "avatar": "/avatars/designer.png",
        "system": "你是 UI 设计师，负责界面设计和用户体验。输出具体的布局、配色、交互细节。",
    },
    "frontend": {
        "name": "前端工程师",
        "avatar": "/avatars/frontend.png",
        "system": "你是前端工程师，负责用 React/TypeScript 实现界面。代码简洁、组件化、无 bug。",
    },
    "backend": {
        "name": "后端工程师",
        "avatar": "/avatars/backend.png",
        "system": "你是后端工程师，负责 API 设计和数据逻辑。代码健壮、安全、可测试。",
    },
    "tester": {
        "name": "测试工程师",
        "avatar": "/avatars/tester.png",
        "system": "你是测试工程师，负责验证功能正确性和边界情况。输出具体的测试用例和结果。",
    },
    "ops": {
        "name": "运维工程师",
        "avatar": "/avatars/ops.png",
        "system": "你是运维工程师，负责部署、监控和稳定性。输出具体的配置和检查步骤。",
    },
}


def build_worker_messages(role: str, task: str) -> list[dict]:
    """构建 sub-agent 的初始消息列表。"""
    persona = ROLES.get(role, ROLES["pm"])
    return [
        {"role": "system", "content": persona["system"]},
        {"role": "user", "content": f"你的任务：{task}"},
    ]


def get_role_info(role: str) -> dict:
    """获取角色信息（名字、头像）。"""
    return ROLES.get(role, ROLES["pm"])
