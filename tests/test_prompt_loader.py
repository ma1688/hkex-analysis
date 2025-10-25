"""测试提示词配置化加载机制"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.utils.prompts import get_prompt_loader, PLANNER_SYSTEM_PROMPT, DOCUMENT_AGENT_SYSTEM_PROMPT


def test_prompt_loader():
    """测试提示词加载器"""
    print("=" * 80)
    print("测试提示词配置化加载机制")
    print("=" * 80)
    
    loader = get_prompt_loader()
    
    # 测试1: 加载 Planner 提示词
    print("\n[测试1] 加载 Planner 系统提示词")
    planner_prompt = loader.get_prompt("planner_system_prompt", PLANNER_SYSTEM_PROMPT)
    
    is_from_config = (planner_prompt != PLANNER_SYSTEM_PROMPT)
    print(f"  ✓ 提示词已加载")
    print(f"  ✓ 来源: {'配置文件' if is_from_config else '硬编码默认值'}")
    print(f"  ✓ 长度: {len(planner_prompt)} 字符")
    print(f"  ✓ 预览: {planner_prompt[:100]}...")
    
    # 测试2: 加载 Document Agent 提示词
    print("\n[测试2] 加载 Document Agent 系统提示词")
    doc_agent_prompt = loader.get_prompt("document_agent_system_prompt", DOCUMENT_AGENT_SYSTEM_PROMPT)
    
    is_from_config = (doc_agent_prompt != DOCUMENT_AGENT_SYSTEM_PROMPT)
    print(f"  ✓ 提示词已加载")
    print(f"  ✓ 来源: {'配置文件' if is_from_config else '硬编码默认值'}")
    print(f"  ✓ 长度: {len(doc_agent_prompt)} 字符")
    print(f"  ✓ 预览: {doc_agent_prompt[:100]}...")
    
    # 测试3: 加载 Few-Shot 示例
    print("\n[测试3] 加载 Planner Few-Shot 示例")
    few_shot = loader.get_prompt("planner_few_shot_examples")
    
    if few_shot:
        print(f"  ✓ Few-Shot 示例已加载")
        print(f"  ✓ 示例数量: {len(few_shot)}")
        print(f"  ✓ 第一个示例查询: {few_shot[0].get('query', 'N/A')}")
    else:
        print(f"  ✓ 未找到配置，将使用硬编码默认值")
    
    # 测试4: 测试不存在的提示词（应返回默认值）
    print("\n[测试4] 测试不存在的提示词（应返回默认值）")
    default_value = "This is a default value"
    result = loader.get_prompt("nonexistent_prompt", default_value)
    
    if result == default_value:
        print(f"  ✓ 正确返回默认值")
    else:
        print(f"  ✗ 错误：应返回默认值")
    
    # 测试5: 检查配置文件路径
    print("\n[测试5] 检查配置文件路径")
    prompts_dir = loader.prompts_dir
    print(f"  ✓ 配置目录: {prompts_dir}")
    print(f"  ✓ 目录存在: {prompts_dir.exists()}")
    
    prompts_file = prompts_dir / "prompts.yaml"
    print(f"  ✓ 配置文件: {prompts_file}")
    print(f"  ✓ 文件存在: {prompts_file.exists()}")
    
    if prompts_file.exists():
        print(f"  ✓ 文件大小: {prompts_file.stat().st_size} 字节")
    
    print("\n" + "=" * 80)
    print("✓ 所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_prompt_loader()

